import sys, asyncio
from playwright.async_api import async_playwright
async def main(path, out, reveal):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = await b.new_page(viewport={'width':820,'height':1400})
        await pg.goto('file://'+path)
        if reveal=='1':
            await pg.click('#revealall')
        await pg.screenshot(path=out, full_page=True)
        await b.close()
asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else '0'))
