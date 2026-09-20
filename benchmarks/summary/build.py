"""Build the self-contained scorecard; optionally export a PNG with Playwright."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png', type=Path)
    parser.add_argument('--metric', choices=['ratio', 'ms'], default='ratio')
    parser.add_argument('--browser', help='Optional Chromium executable path')
    args = parser.parse_args()
    data = json.loads((ROOT / 'data.json').read_text())
    for row in data['rows']:
        assert len(row['ms']) == 6
        assert all(v is None or v > 0 for v in row['ms'])
    template = (ROOT / 'template.html').read_text()
    assert template.count('__DATA__') == 1
    html = ROOT / 'index.html'
    html.write_text(template.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')))
    print(html)
    if args.png:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options = {'headless': True, 'args': ['--disable-gpu']}
            if args.browser:
                options['executable_path'] = args.browser
            browser = p.chromium.launch(**options)
            page = browser.new_page(viewport={'width': 1500, 'height': 1000}, device_scale_factor=2)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(html.as_uri() + '?metric=' + args.metric)
            page.wait_for_function('window.scorecardReady === true')
            assert not errors, errors
            assert page.locator('tbody th.label').count() == len(data['rows'])
            assert page.locator('tbody tr:not(.section) td').count() == len(data['rows']) * 6
            assert page.evaluate('document.querySelector("#scorecard").scrollWidth <= document.querySelector("#scorecard").clientWidth')
            args.png.parent.mkdir(parents=True, exist_ok=True)
            page.locator('#scorecard').screenshot(path=str(args.png))
            print(args.png)
            browser.close()


if __name__ == '__main__':
    main()
