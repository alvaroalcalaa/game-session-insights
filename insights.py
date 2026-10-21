"""Analítica local de sesiones de videojuegos. Python 3.10+, biblioteca estándar."""
import argparse
import csv
import html
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
COLUMNS = {"session_id", "player_id", "start_at", "end_at"}


@dataclass(frozen=True)
class Session:
    session_id: str
    player_id: str
    start: datetime
    end: datetime

    @property
    def minutes(self):
        return (self.end - self.start).total_seconds() / 60


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("la fecha necesita zona horaria (Z o +hh:mm)")
    return result.astimezone(UTC)


def read_sessions(path):
    sessions, seen = [], set()
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("faltan columnas: " + ", ".join(sorted(COLUMNS)))
        for line, row in enumerate(reader, 2):
            try:
                sid, pid = row["session_id"].strip(), row["player_id"].strip()
                if not sid or not pid:
                    raise ValueError("session_id y player_id no pueden estar vacíos")
                if sid in seen:
                    raise ValueError("session_id duplicado: " + sid)
                start, end = timestamp(row["start_at"]), timestamp(row["end_at"])
                if end < start:
                    raise ValueError("end_at es anterior a start_at")
                sessions.append(Session(sid, pid, start, end))
                seen.add(sid)
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(f"fila {line}: {error}") from error
    return sessions


def analyze(sessions, as_of):
    """as_of es el último día UTC cuya observación está completa."""
    cutoff = datetime.combine(as_of + timedelta(days=1), time.min, UTC)
    included = [s for s in sessions if s.start < cutoff and s.end < cutoff]
    activity, first, daily = defaultdict(set), {}, defaultdict(list)
    for s in included:
        day = s.start.date()
        activity[s.player_id].add(day)
        first[s.player_id] = min(day, first.get(s.player_id, day))
        daily[day].append(s)
    cohorts = []
    for day in sorted(set(first.values())):
        players = {p for p, joined in first.items() if joined == day}
        cohort = {"date": day.isoformat(), "players": len(players)}
        for horizon in (1, 7):
            mature = day + timedelta(days=horizon) <= as_of
            retained = sum(day + timedelta(days=horizon) in activity[p]
                           for p in players) if mature else None
            cohort[f"d{horizon}"] = {
                "eligible": len(players) if mature else 0,
                "retained": retained,
                "rate": round(retained / len(players), 4) if mature else None,
            }
        cohorts.append(cohort)
    retention = {}
    for horizon in (1, 7):
        cells = [c[f"d{horizon}"] for c in cohorts]
        eligible = sum(c["eligible"] for c in cells)
        retained = sum(c["retained"] or 0 for c in cells)
        retention[f"d{horizon}"] = {
            "eligible": eligible, "retained": retained if eligible else None,
            "rate": round(retained / eligible, 4) if eligible else None,
        }
    days = []
    if daily:
        day = min(daily)
        while day <= as_of:
            rows = daily.get(day, [])
            days.append({
                "date": day.isoformat(),
                "active_players": len({s.player_id for s in rows}),
                "sessions": len(rows),
                "minutes": round(sum(s.minutes for s in rows), 2),
            })
            day += timedelta(days=1)
    durations = [s.minutes for s in included]
    return {
        "as_of_utc": as_of.isoformat(),
        "input_sessions": len(sessions), "sessions": len(included),
        "excluded_sessions": len(sessions) - len(included),
        "players": len(first),
        "total_minutes": round(sum(durations), 2),
        "median_session_minutes": round(statistics.median(durations), 2) if durations else None,
        "retention": retention, "daily": days, "cohorts": cohorts,
    }


def percent(value):
    return "No observable" if value is None else f"{100 * value:.1f}%"


def render_html(report, title="Game Session Insights"):
    escape = html.escape
    daily = "".join(
        f'<tr><td>{escape(d["date"])}</td><td>{d["active_players"]}</td>'
        f'<td>{d["sessions"]}</td><td>{d["minutes"]}</td></tr>'
        for d in report["daily"])
    cohorts = "".join(
        f'<tr><td>{escape(c["date"])}</td><td>{c["players"]}</td>'
        f'<td>{percent(c["d1"]["rate"])}</td><td>{percent(c["d7"]["rate"])}</td></tr>'
        for c in report["cohorts"])
    cards = "".join(
        f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in [
            ("Jugadores observados", report["players"]),
            ("Sesiones completas", report["sessions"]),
            ("Minutos registrados", report["total_minutes"]),
            ("Retención D1", percent(report["retention"]["d1"]["rate"])),
            ("Retención D7", percent(report["retention"]["d7"]["rate"])),
        ])
    return f"""<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(title)}</title>
<style>
body{{font:16px system-ui,sans-serif;background:#0d1424;color:#e8efff;margin:0}}
main{{max-width:1080px;margin:auto;padding:40px 24px}}
h1{{font-size:36px;letter-spacing:-1px}} p,span{{color:#b3c1dc}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:28px 0}}
.card{{background:#18243b;border:1px solid #2b3e5b;padding:20px;border-radius:14px;flex:1;min-width:145px}}
strong{{display:block;font-size:28px;color:#71e0cf;margin-top:8px}}
section{{margin-top:32px}}table{{border-collapse:collapse;width:100%;background:#141f34}}
th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #2b3e5b}}
th{{color:#71e0cf}}.scroll{{overflow:auto}}.note{{line-height:1.6;font-size:14px}}
</style><main><p>ANALÍTICA DE VIDEOJUEGOS · DATOS LOCALES</p>
<h1>{escape(title)}</h1>
<p>Observación completa hasta {escape(report["as_of_utc"])} (UTC)</p>
<div class="cards">{cards}</div>
<section><h2>Actividad por día de inicio</h2><div class="scroll"><table>
<thead><tr><th>Fecha UTC</th><th>Jugadores</th><th>Sesiones</th><th>Minutos</th></tr></thead>
<tbody>{daily}</tbody></table></div></section>
<section><h2>Cohortes de primera sesión observada</h2><div class="scroll"><table>
<thead><tr><th>Cohorte</th><th>Jugadores</th><th>D1</th><th>D7</th></tr></thead>
<tbody>{cohorts}</tbody></table></div></section>
<p class="note">D1 y D7 miden regreso en el día calendario exacto, no dentro de una ventana.
Los porcentajes globales ponderan solo jugadores de cohortes maduras. «No observable»
indica que aún no se ha completado ese día. La primera sesión del archivo puede no ser
el alta real. Sesiones excluidas por finalizar fuera del corte: {report["excluded_sessions"]}.
La ausencia de actividad solo es interpretable si la captura de datos está completa.
No contiene predicciones de abandono ni inferencias causales.</p></main></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat,
                        help="Último día completo observado, YYYY-MM-DD, en UTC")
    parser.add_argument("--json", type=Path, dest="json_path")
    parser.add_argument("--html", type=Path, dest="html_path")
    args = parser.parse_args()
    outputs = [p.resolve() for p in (args.json_path, args.html_path) if p]
    if len(set(outputs)) != len(outputs) or args.csv.resolve() in outputs:
        parser.error("las salidas deben ser distintas entre sí y del CSV de entrada")
    try:
        report = analyze(read_sessions(args.csv), args.as_of)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.json_path:
            args.json_path.write_text(payload, encoding="utf-8")
        if args.html_path:
            args.html_path.write_text(render_html(report), encoding="utf-8")
        print(payload, end="")
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
