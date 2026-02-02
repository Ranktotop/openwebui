import json
import sys
import os
from datetime import datetime


def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("Bitte Dateinamen eingeben (z. B. requests.json): ").strip()
        if not input_file:
            input_file = 'requests.json'

    if not os.path.exists(input_file):
        print(f"❌ Fehler: Datei '{input_file}' nicht gefunden.")
        return

    out_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_file = f"extracted-logs_{out_timestamp}.txt"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(output_file, 'w', encoding='utf-8') as out:
            entries = data.get('log', {}).get('entries', [])

            for entry in entries:
                if entry.get('_resourceType') == 'websocket':
                    messages = entry.get('_webSocketMessages', [])

                    for msg in messages:
                        payload = msg.get('data', '').strip()

                        # FILTER: Erlaube JSON ODER die "start"-Nachricht
                        if payload.startswith('{') or payload.startswith('start '):
                            unix_time = msg.get('time', 0)
                            dt = datetime.fromtimestamp(unix_time)
                            time_formatted = dt.strftime("%H:%M:%S.%f")[:-3]

                            out.write(f"{payload}\t{len(payload)}\n")
                            out.write(f"{time_formatted}\n")

        print(f"✅ Fertig! Start-Zeile und JSON extrahiert in: {output_file}")

    except Exception as e:
        print(f"❌ Fehler: {e}")


if __name__ == "__main__":
    main()
