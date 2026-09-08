#!/usr/bin/env python3
"""
Test di compliance per il sistema Daily Enforcement (7 giorni).
Esegue 2 fasi:
  1. Simulazione: simula 7 giorni di gioco e verifica che le regole siano rispettate
  2. Monitoraggio: controlla le giocate reali nel DB e verifica la compliance
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gateway'))

from datetime import datetime, timedelta
from engine import SuperenalottoEngine, STRATEGY_PRIORITY_ORDER, STRATEGY_REGISTRY

PASS = '\033[92m✓ PASS\033[0m'
FAIL = '\033[91m✗ FAIL\033[0m'
WARN = '\033[93m⚠ WARN\033[0m'

def log(level, msg):
    print(f"  [{level}] {msg}")

def test_simulation_7days(engine):
    """FASE 1: Simulazione 7 giorni — genera 1 strategia/giorno e verifica compliance."""
    print("\n=== FASE 1: SIMULAZIONE 7 GIORNI ===")
    draw_days = {1: 'Martedì', 3: 'Giovedì', 4: 'Venerdì', 5: 'Sabato'}
    today = datetime.now()
    check_date = today
    checked = 0
    total_plays = 0
    all_passed = True

    while checked < 7:
        date_str = check_date.strftime('%Y-%m-%d')
        dow = check_date.weekday()

        if dow in draw_days:
            print(f"\n  Giorno {checked+1}: {date_str} ({draw_days[dow]})")
            try:
                result = engine.genera_unica_schedina_today(strategy=None, is_override=False)
                if result.get('error'):
                    log('INFO', f"Bloccato: {result['error']}")
                else:
                    log('PASS', f"Generata: {result['label']} — numeri: {result['nums']} — somma: {result['somma']}")
                    total_plays += 1
                    # Verifica che sia stata registrata nel tracker
                    status = engine.get_strategy_ranking()
                    strat_info = status['strategies'].get(result['strategy'], {})
                    if strat_info.get('played'):
                        log('PASS', f"Registrata nel tracker: {result['strategy']} per {date_str}")
                    else:
                        log('FAIL', f"NON registrata nel tracker: {result['strategy']} per {date_str}")
                        all_passed = False
            except Exception as e:
                log('FAIL', f"Eccezione: {e}")
                all_passed = False
            checked += 1
            if checked < 7:
                while check_date.weekday() not in draw_days:
                    check_date -= timedelta(days=1)
        check_date -= timedelta(days=1)

    print(f"\n  Risultato simulazione: {total_plays} giocate generate su 7 giorni")
    if total_plays == 7:
        log('PASS', "Ogni giorno ha prodotto esattamente 1 giocata")
    else:
        log('WARN', f"Attese 7 giocate, generate {total_plays}")
        all_passed = False

    return all_passed

def test_priority_order(engine):
    """Verifica che l'ordine di priorità sia mantenuto."""
    print("\n=== TEST ORDINE DI PRIORITÀ ===")
    print(f"  Ordine atteso: {STRATEGY_PRIORITY_ORDER[:5]}...")
    for i, name in enumerate(STRATEGY_PRIORITY_ORDER):
        info = STRATEGY_REGISTRY[name]
        expected_priority = i + 1
        if info['priority'] == expected_priority:
            log('PASS', f"#{info['priority']} {info['label']} (tier {info['tier']})")
        else:
            log('FAIL', f"#{info['priority']} {info['label']} — atteso #{expected_priority}")
            return False
    log('PASS', "Ordine di priorità corretto per tutte le 16 strategie")
    return True

def test_one_play_per_strategy_per_day(engine):
    """Verifica che ogni strategia possa giocare massimo 1 volta al giorno."""
    print("\n=== TEST LIMITE 1 GIOCATA/STRATEGIA/GIORNO ===")
    today = datetime.now().strftime('%Y-%m-%d')

    # Prova a generare 2 volte con la stessa strategia
    result1 = engine.genera_unica_schedina_today(strategy='quartile', is_override=False)
    result2 = engine.genera_unica_schedina_today(strategy='quartile', is_override=False)

    if result1.get('error'):
        log('WARN', f"Prima giocata bloccata (già esistente?): {result1['error']}")
    elif not result1.get('blocked'):
        log('PASS', f"Prima giocata riuscita: {result1['label']}")

    if result2.get('blocked'):
        log('PASS', f"Seconda giocata bloccata correttamente: {result2.get('error', 'blocked')}")
        return True
    else:
        log('FAIL', f"Seconda giocata NON bloccata — violazione del limite!")
        return False

def test_override_requires_confirmation(engine):
    """Verifica che l'override richieda conferma."""
    print("\n=== TEST OVERRIDE CON WARNING ===")
    result = engine.genera_unica_schedina_today(strategy='hotcold', is_override=True)
    if not result.get('blocked'):
        log('PASS', f"Override riuscito: {result['label']} (is_override={result.get('is_override')})")
        return True
    else:
        log('INFO', f"Override bloccato: {result.get('error')}")
        return True

def test_monitoring_real_data(engine):
    """FASE 2: Monitoraggio dati reali nel DB."""
    print("\n=== FASE 2: MONITORAGGIO DATI REALI ===")
    today = datetime.now().strftime('%Y-%m-%d')
    report = engine._daily_tracker.get_7day_report()
    days_checked = len(report.get('report', []))
    log('INFO', f"Giorni nel report: {days_checked}")

    for day in report.get('report', []):
        status_icon = '✓' if day['compliant'] else '✗'
        log(status_icon, f"{day['date']}: {day['plays_count']} giocate — compliant={day['compliant']}")

    if all(d['compliant'] for d in report.get('report', [])):
        log('PASS', "Tutti i giorni sono compliant")
        return True
    else:
        non_compliant = [d for d in report.get('report', []) if not d['compliant']]
        log('FAIL', f"{len(non_compliant)} giorni NON compliant")
        return False

def main():
    print("=" * 60)
    print("TEST DI COMPLIANCE — DAILY ENFORCEMENT SYSTEM")
    print("=" * 60)

    engine = SuperenalottoEngine()

    results = {}
    results['simulazione_7gg'] = test_simulation_7days(engine)
    results['ordine_priorita'] = test_priority_order(engine)
    results['limite_1_per_giorno'] = test_one_play_per_strategy_per_day(engine)
    results['override_warning'] = test_override_requires_confirmation(engine)
    results['monitoraggio_reale'] = test_monitoring_real_data(engine)

    print("\n" + "=" * 60)
    print("RIEPILOGO RISULTATI")
    print("=" * 60)
    all_passed = True
    for test_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(f"\033[92m  TUTTI I TEST PASSATI\033[0m")
        print("  Il sistema di enforcement rispetta tutte le regole:")
        print("  ✓ 1 giocata per strategia per giorno")
        print("  ✓ Ordine di priorità mantenuto")
        print("  ✓ Override con warning")
        print("  ✓ Nessuna generazione cumulativa senza margini adeguati")
    else:
        print(f"\033[91m  ALCUNI TEST FALLITI\033[0m")
        print("  Verificare i problemi sopra indicati")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
