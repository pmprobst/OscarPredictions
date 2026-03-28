from playwright.sync_api import sync_playwright
import argparse
import csv
import os
import re

CSV_FILE = "movies.csv"
# Appending to an existing movies.csv that was created with fewer columns will misalign rows;
# use a new file or migrate headers before adding new fields.


def _imdb_browser_context(playwright, headless: bool):
    """Launch Chromium and return (browser, context) to reduce IMDb 403 / empty-shell responses."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/Los_Angeles",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
        },
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return browser, context


def get_critics_choice(browser, movie_url):
    page = browser.new_page()
    try:
        # find table of movies
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        try:
            # find critics choice awards
            page.get_by_label("Jump to").select_option("#ev0000133")    # code for critics choice in dropdown
            page.wait_for_timeout(1000)
        except:
            return {"critics_choice_nom": 0, "critics_choice_win": 0}

        # find list items for best picture awards
        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if "Critics Choice Award" in text and "Best Picture" in text:
                # nom = 1 if movie was nominated
                if "Nominee" in text:
                    nom = 1
                
                # nom and win = 1 if movie won
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"critics_choice_nom": nom, "critics_choice_win": win}

    except:
        # nom and win = 0 if movie was not nominated
        return {"critics_choice_nom": 0, "critics_choice_win": 0}

    finally:
        page.close()

def get_bafta(browser, movie_url):
    page = browser.new_page()
    try:
        # find table of movies
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        try:
            # find bafta awards
            page.get_by_label("Jump to").select_option("#ev0000123")    # code for critics choice in dropdown
            page.wait_for_timeout(1000)
        except:
            return {"bafta_nom": 0, "bafta_win": 0}

        # find list items for best picture awards
        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if (
                "BAFTA Film Award" in text
                and "Best Film" in text
                and "Not in the English Language" not in text
            ):
                # nom = 1 if movie was nominated
                if "Nominee" in text:
                    nom = 1
                
                # nom and win = 1 if movie won
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"bafta_nom": nom, "bafta_win": win}

    except:
        # nom and win = 0 if movie was not nominated
        return {"bafta_nom": 0, "bafta_win": 0}

    finally:
        page.close()

def get_golden_globes(browser, movie_url):
    page = browser.new_page()
    try:
        # find table of movies
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        try:
            # find bafta awards
            page.get_by_label("Jump to").select_option("#ev0000292")    # code for critics choice in dropdown
            page.wait_for_timeout(1000)
        except:
            return {"golden_globes_nom": 0, "golden_globes_win": 0}

        # find list items for best picture awards
        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if (
                "Golden Globe" in text
                and (
                    "Best Motion Picture - Musical or Comedy" in text
                    or "Best Motion Picture - Drama" in text
                )
            ):
                # nom = 1 if movie was nominated
                if "Nominee" in text:
                    nom = 1
                
                # nom and win = 1 if movie won
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"golden_globes_nom": nom, "golden_globes_win": win}

    except:
        # nom and win = 0 if movie was not nominated
        return {"golden_globes_nom": 0, "golden_globes_win": 0}

    finally:
        page.close()

def get_pga(browser, movie_url):
    page = browser.new_page()
    try:
        # find table of movies
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        try:
            # find bafta awards
            page.get_by_label("Jump to").select_option("#ev0000531")    # code for critics choice in dropdown
            page.wait_for_timeout(1000)
        except:
            return {"pga_nom": 0, "pga_win": 0}

        # find list items for best picture awards
        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if (
                (
                    "Darryl F. Zanuck Award" in text
                    or "PGA Award" in text
                )
                and "Outstanding Producer of Theatrical Motion Pictures" in text
            ):
                # nom = 1 if movie was nominated
                if "Nominee" in text:
                    nom = 1
                
                # nom and win = 1 if movie won
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"pga_nom": nom, "pga_win": win}

    except:
        # nom and win = 0 if movie was not nominated
        return {"pga_nom": 0, "pga_win": 0}

    finally:
        page.close()

def get_sag(browser, movie_url):
    page = browser.new_page()
    try:
        # find table of movies
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        try:
            # find bafta awards
            page.get_by_label("Jump to").select_option("#ev0000598")    # code for critics choice in dropdown
            page.wait_for_timeout(1000)
        except:
            return {"sag_nom": 0, "sag_win": 0}
        
        section = page.get_by_test_id("sub-section-ev0000598")
        buttons = section.locator('button:has-text("more")')

        for i in range(buttons.count()):
            try:
                buttons.nth(i).click()
            except:
                pass

        # find list items for best picture awards
        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if (
                "Actor" in text
                and 
                (
                    "Outstanding Performance by a Cast in a Motion Picture" in text
                    or "Outstanding Performance by a Cast" in text
                )
            ):
                # nom = 1 if movie was nominated
                if "Nominee" in text:
                    nom = 1
                
                # nom and win = 1 if movie won
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"sag_nom": nom, "sag_win": win}

    except:
        # nom and win = 0 if movie was not nominated
        return {"sag_nom": 0, "sag_win": 0}

    finally:
        page.close()


def _director_nm_id_from_title_page(page):
    """First billed director link on the title page (/name/nm…)."""
    rows = page.locator('[data-testid="title-pc-principal-credit"]').filter(has_text="Director")
    if rows.count() == 0:
        return None
    link = rows.first.locator('a[href^="/name/nm"]').first
    if link.count() == 0:
        return None
    href = link.get_attribute("href") or ""
    m = re.search(r"/name/(nm\d+)", href)
    return m.group(1) if m else None


def get_director_award_counts(browser, movie_url, oscar_year):
    """
    Count director award rows on IMDb through oscar_year (inclusive).
    Wins also count toward nominations (Option A).
    """
    page = browser.new_page()
    try:
        base = movie_url.split("?")[0].rstrip("/")
        page.goto(base, timeout=60000)
        page.wait_for_selector("body", timeout=60000)
        nm_id = _director_nm_id_from_title_page(page)
        if not nm_id:
            return {"director_award_noms": 0, "director_award_wins": 0}

        awards_url = f"https://www.imdb.com/name/{nm_id}/awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body", timeout=60000)

        noms = 0
        wins = 0
        items = page.locator("main li")
        if items.count() == 0:
            items = page.locator("li")
        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if "Nominee" not in text and "Winner" not in text:
                continue
            years = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", text)]
            if not years:
                continue
            award_year = max(years)
            if award_year > oscar_year:
                continue
            if "Winner" in text:
                wins += 1
                noms += 1
            elif "Nominee" in text:
                noms += 1

        return {"director_award_noms": noms, "director_award_wins": wins}
    except Exception:
        return {"director_award_noms": 0, "director_award_wins": 0}
    finally:
        page.close()


def get_movies_for_year(browser, year, writer):
    # Oscar ceremony list page (IMDb uses /oscars/event/ for newer UX; /event/ still used in places)
    urls = (
        f"https://www.imdb.com/oscars/event/ev0000003/{year}/1/",
        f"https://www.imdb.com/event/ev0000003/{year}/1/",
    )
    page = browser.new_page()
    try:
        category = None
        for url in urls:
            try:
                page.goto(url, timeout=90000, wait_until="load")
            except Exception:
                continue
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-testid]').length > 0",
                    timeout=45000,
                )
            except Exception:
                pass
            picture_testids = page.evaluate(
                """() => {
                  const ids = [];
                  document.querySelectorAll('[data-testid]').forEach(el => {
                    const t = el.getAttribute('data-testid');
                    if (t && /best/i.test(t) && /picture/i.test(t)) ids.push(t);
                  });
                  return [...new Set(ids)];
                }"""
            )
            try_order = []
            for tid in ("BestPicture", "BestMotionPictureoftheYear"):
                if tid not in try_order:
                    try_order.append(tid)
            for tid in picture_testids:
                if tid not in try_order:
                    try_order.append(tid)
            for tid in try_order:
                loc = page.locator(f'[data-testid="{tid}"]')
                try:
                    loc.first.wait_for(state="visible", timeout=25000)
                except Exception:
                    continue
                if loc.count() > 0:
                    category = loc
                    break
            if category is not None:
                break
        if category is None:
            print(f"No best picture section found for {year}")
            return

        links = category.locator("a.ipc-title-link-wrapper:has(h3)")

        for i in range(links.count()):
            link = links.nth(i)
            title = link.locator("h3").inner_text()
            href = link.get_attribute("href")
            if not href or "/title/" not in href:
                continue
            full_url = "https://www.imdb.com" + href
            print(f"Processing {title} ({year})")

            cc_result = get_critics_choice(browser, full_url)
            print(f"  Critics Choice Nominee: {cc_result['critics_choice_nom']}, Winner: {cc_result['critics_choice_win']}")

            bafta_result = get_bafta(browser, full_url)
            print(f"  BAFTA Nominee: {bafta_result['bafta_nom']}, Winner: {bafta_result['bafta_win']}")

            gg_result = get_golden_globes(browser, full_url)
            print(f"  Golden Globes Nominee: {gg_result['golden_globes_nom']}, Winner: {gg_result['golden_globes_win']}")

            pga_result = get_pga(browser, full_url)
            print(f"  PGA Nominee: {pga_result['pga_nom']}, Winner: {pga_result['pga_win']}")

            sag_result = get_sag(browser, full_url)
            print(f"  SAG Nominee: {sag_result['sag_nom']}, Winner: {sag_result['sag_win']}")

            director_awards = get_director_award_counts(browser, full_url, year)
            print(
                f"  Director awards (through {year}): noms={director_awards['director_award_noms']}, wins={director_awards['director_award_wins']}"
            )

            movie = {"title": title, "url": full_url, "year": year}
            movie.update(cc_result)
            movie.update(bafta_result)
            movie.update(gg_result)
            movie.update(pga_result)
            movie.update(sag_result)
            movie.update(director_awards)

            writer.writerow(movie)
    finally:
        page.close()


FIELDNAMES = [
    "title",
    "url",
    "year",
    "critics_choice_nom",
    "critics_choice_win",
    "bafta_nom",
    "bafta_win",
    "golden_globes_nom",
    "golden_globes_win",
    "pga_nom",
    "pga_win",
    "sag_nom",
    "sag_win",
    "director_award_noms",
    "director_award_wins",
]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape IMDb Best Picture nominees and precursor / director award fields."
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="Y",
        help="Single Oscar ceremony year to scrape (for a quick test). Default: 2026 through 1996.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
    )
    parser.add_argument(
        "--csv",
        default=CSV_FILE,
        help=f"Output CSV path (default: {CSV_FILE}).",
    )
    args = parser.parse_args()

    if args.year is not None:
        years = [args.year]
    else:
        years = list(range(2026, 1995, -1))

    out_path = args.csv
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if f.tell() == 0:
            writer.writeheader()

        with sync_playwright() as p:
            browser, context = _imdb_browser_context(p, args.headless)
            try:
                for year in years:
                    try:
                        get_movies_for_year(context, year, writer)
                        f.flush()
                    except Exception as e:
                        print(f"Error processing {year}: {e}")
            finally:
                context.close()
                browser.close()

    print(f"Movies written incrementally to {out_path}")


if __name__ == "__main__":
    main()