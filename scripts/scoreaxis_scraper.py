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


def render_html(matches, existing_html, timestamp):
    if not matches:
        if existing_html:
            return existing_html
        return f"""
        <h1>🏆 askporter Sweepstake Command Center 🏆</h1>
        <div class=\"subtitle\">No World Cup match data available yet — checking again soon.</div>
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
    <div class=\"subtitle\">Auto-updated from OpenLigaDB · {timestamp}</div>
    <section class=\"info-section\">
      <div class=\"guide-box\">
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
