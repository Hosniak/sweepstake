import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = 'https://api.openligadb.de/getmatchdata/worldcup/2026'
OUT_PATH = Path(__file__).resolve().parent.parent / 'sweepstake-data.json'


def fetch_matches():
    req = urllib.request.Request(
        API_URL,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8')
        return json.loads(body)


def load_existing_payload():
    if not OUT_PATH.exists():
        return {}
    try:
        with OUT_PATH.open('r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return {}


def parse_match_time(match):
    for key in ('matchDateTimeUTC', 'matchDateTime', 'MatchDateTimeUTC', 'MatchDateTime'):
        dt_text = match.get(key)
        if isinstance(dt_text, str) and dt_text:
            try:
                return datetime.fromisoformat(dt_text.replace('Z', '+00:00')).strftime('%a %d %b %H:%M UTC')
            except Exception:
                return dt_text
    return 'TBD'


def parse_match_datetime(match):
    for key in ('matchDateTimeUTC', 'matchDateTime', 'MatchDateTimeUTC', 'MatchDateTime'):
        dt_text = match.get(key)
        if isinstance(dt_text, str) and dt_text:
            try:
                return datetime.fromisoformat(dt_text.replace('Z', '+00:00'))
            except Exception:
                continue
    return None


def format_score(match):
    results = match.get('matchResults') or []
    if not isinstance(results, list):
        results = [results]
    for result in results:
        if result.get('resultType') == 'FINAL' or str(result.get('resultName', '')).lower() == 'final':
            return f"{result.get('pointsTeam1', '?')} - {result.get('pointsTeam2', '?')}"
    if results:
        first = results[0]
        return f"{first.get('pointsTeam1', '?')} - {first.get('pointsTeam2', '?')}"
    return 'vs'


def is_live_match(match):
    if match.get('matchIsRunning') or match.get('isLive'):
        return True
    if match.get('matchIsStarted') and not match.get('matchIsFinished'):
        return True
    return False


def is_upcoming_match(match):
    if is_live_match(match):
        return False
    if match.get('matchIsFinished') or match.get('isFinished'):
        return False
    dt = parse_match_datetime(match)
    if dt is None:
        return True
    return dt > datetime.now(timezone.utc)


def render_live_section(live_matches):
    rows = []
    for match in (live_matches or []):
        home = match.get('team1', {}).get('teamName', 'TBD')
        away = match.get('team2', {}).get('teamName', 'TBD')
        score = format_score(match)
        status = 'LIVE'
        time_text = parse_match_time(match)
        rows.append(
            f"<div class=\"team-pill\">"
            f"<div class=\"team-info\"><span class=\"name-container\"><span class=\"team-name\">{home} vs {away}</span>"
            f"<span class=\"group-name\">{time_text} · {status}</span></div></div>"
            f"<div style=\"margin-left:14px;color:#f8fafc;font-size:14px;\">Score: {score}</div>"
        )
    body = ''.join(rows) if rows else '<div class="guide-box"><em>No live matches right now</em></div>'
    return f"""
    <section class=\"info-section\">
      <h2>🔴 LIVE RIGHT NOW</h2>
      {body}
    </section>
    """

def render_upcoming_section(upcoming_matches):
    rows = []
    for match in (upcoming_matches or [])[:3]:
        home = match.get('team1', {}).get('teamName', 'TBD')
        away = match.get('team2', {}).get('teamName', 'TBD')
        time_text = parse_match_time(match)
        rows.append(
            f"<div class=\"team-pill\">"
            f"<div class=\"team-info\">"
            f"<span class=\"name-container\">"
            f"<span class=\"team-name\">{home} vs {away}</span>"
            f"<span class=\"group-name\">{time_text} · Coming up next</span>"
            f"</span></div></div>"
        )
    body = ''.join(rows) if rows else '<div class="guide-box"><em>No upcoming matches scheduled</em></div>'
    return f"""
        <section class=\"info-section\"> 
            <h2>⏳ COMING UP</h2> 
            {body}
        </section>
        """


def render_html(matches, existing_html, timestamp):
    if not matches:
        if existing_html:
            print('No match data returned; preserving existing HTML output')
            return existing_html

        # don't fail hard if the API returned nothing — still render the page
        # with placeholders so the client always sees the LIVE / COMING UP sections.
        note_html = f"""
        <section class=\"info-section\">
            <div class=\"guide-box\">
                <strong>Latest update</strong>
                <ul>
                    <li>OpenLigaDB did not return match data on this run.</li>
                    <li>The sweepstake page will keep using the latest cached content until the next refresh.</li>
                </ul>
            </div>
        </section>
        """
        matches = []

    live_matches = [match for match in matches if is_live_match(match)]
    upcoming_matches = [match for match in matches if is_upcoming_match(match)]
    upcoming_matches.sort(key=lambda match: parse_match_datetime(match) or datetime.max)
    print(f'Found {len(live_matches)} live matches and {len(upcoming_matches)} upcoming matches')

    # show the next up to 3 upcoming matches
    live_html = render_live_section(live_matches)
    upcoming_html = render_upcoming_section(upcoming_matches[:3])

    rows = []
    for match in matches[:8]:
        home = match.get('team1', {}).get('teamName', 'TBD')
        away = match.get('team2', {}).get('teamName', 'TBD')
        score = match.get('matchResults', [{}])
        score_text = 'vs'
        if score:
            for result in score:
                if result.get('resultType') == 'FINAL':
                    score_text = f"{result.get('pointsTeam1', '?')} - {result.get('pointsTeam2', '?')}"
                    break
        rows.append(f"<li><strong>{home}</strong> vs <strong>{away}</strong> — {score_text}</li>")

    return f"""
    <h1>🏆 askporter Sweepstake Command Center 🏆</h1>
    <div class="subtitle">Auto-updated from OpenLigaDB · {timestamp}</div>
    {note_html}
    {live_html}
    {upcoming_html}
    <section class="info-section">
      <div class="guide-box">
        <strong>Latest World Cup data</strong>
        <ul>{''.join(rows)}</ul>
      </div>
    </section>
    """


def main():
    existing_payload = load_existing_payload()
    existing_html = existing_payload.get('html', '')
    timestamp = datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')

    try:
        matches = fetch_matches()
    except Exception as exc:
        print(f'Could not fetch data: {exc}')
        matches = []

    payload = {
        'title': 'askporter World Cup Sweepstake',
        'updatedAt': timestamp,
        'html': render_html(matches, existing_html, timestamp),
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT_PATH} with {len(matches)} matches')


if __name__ == '__main__':
    main()
