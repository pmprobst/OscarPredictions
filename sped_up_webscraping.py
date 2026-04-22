from playwright.sync_api import sync_playwright
import csv

CSV_FILE = "movies.csv"

def get_all_awards(browser, movie_url):
    page = browser.new_page()

    results = {
        "critics_choice_nom": 0, "critics_choice_win": 0,
        "bafta_nom": 0, "bafta_win": 0,
        "golden_globes_nom": 0, "golden_globes_win": 0,
        "pga_nom": 0, "pga_win": 0,
        "sag_nom": 0, "sag_win": 0
    }

    try:
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url)

        page.wait_for_selector("li")

        # 🔥 faster expansion (same behavior, fewer calls)
        buttons = page.locator('button:has-text("more")')
        count = buttons.count()
        for i in range(count):
            try:
                buttons.nth(i).click()
            except:
                pass

        items = page.locator("li")
        item_count = items.count()

        for i in range(item_count):
            text = items.nth(i).inner_text()

            # Critics Choice (UNCHANGED)
            if "Critics Choice Award" in text and "Best Picture" in text:
                if "Nominee" in text:
                    results["critics_choice_nom"] = 1
                if "Winner" in text:
                    results["critics_choice_win"] = 1
                    results["critics_choice_nom"] = 1

            # BAFTA (ONLY fix = exclusion)
            if "BAFTA Film Award" in text and "Best Film" in text:
                if "Best Film Not in the English Language" in text:
                    continue

                if "Nominee" in text:
                    results["bafta_nom"] = 1
                if "Winner" in text:
                    results["bafta_win"] = 1
                    results["bafta_nom"] = 1

            # Golden Globes (UNCHANGED)
            if "Golden Globe" in text and (
                "Best Motion Picture - Drama" in text or
                "Best Motion Picture - Musical or Comedy" in text
            ):
                if "Nominee" in text:
                    results["golden_globes_nom"] = 1
                if "Winner" in text:
                    results["golden_globes_win"] = 1
                    results["golden_globes_nom"] = 1

            # PGA (UNCHANGED)
            if (
                "Darryl F. Zanuck Award" in text or
                "PGA Award" in text
            ) and "Outstanding Producer of Theatrical Motion Pictures" in text:
                if "Nominee" in text:
                    results["pga_nom"] = 1
                if "Winner" in text:
                    results["pga_win"] = 1
                    results["pga_nom"] = 1

            # SAG (UNCHANGED — includes "Actor" exactly as you had it)
            if (
                "Screen Actors Guild Award" in text and
                "Outstanding Performance by a Cast in a Motion Picture" in text and
                "Actor" in text
            ):
                if "Nominee" in text:
                    results["sag_nom"] = 1
                if "Winner" in text:
                    results["sag_win"] = 1
                    results["sag_nom"] = 1

        return results

    except:
        return results

    finally:
        page.close()


def get_movies_for_year(browser, year, writer):
    url = f"https://www.imdb.com/event/ev0000003/{year}/1/"
    page = browser.new_page()
    page.goto(url)

    try:
        try:
            page.wait_for_selector('[data-testid="BestMotionPictureoftheYear"]', timeout=5000)
            category = page.locator('[data-testid="BestMotionPictureoftheYear"]')
        except:
            page.wait_for_selector('[data-testid="BestPicture"]', timeout=5000)
            category = page.locator('[data-testid="BestPicture"]')
    except:
        print(f"No best picture section found for {year}")
        page.close()
        return

    links = category.locator("a.ipc-title-link-wrapper:has(h3)")
    link_count = links.count()

    for i in range(link_count):
        link = links.nth(i)

        title = link.locator("h3").inner_text()
        href = link.get_attribute("href")

        if not href or "/title/" not in href:
            continue

        full_url = "https://www.imdb.com" + href
        print(f"Processing {title} ({year})")

        results = get_all_awards(browser, full_url)

        movie = {"title": title, "url": full_url, "year": year}
        movie.update(results)

        writer.writerow(movie)

    page.close()


# MAIN
with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "title","url","year",
            "critics_choice_nom","critics_choice_win",
            "bafta_nom","bafta_win",
            "golden_globes_nom","golden_globes_win",
            "pga_nom","pga_win",
            "sag_nom","sag_win"
        ]
    )

    if f.tell() == 0:
        writer.writeheader()

    with sync_playwright() as p:
        # 🔥 biggest speed boost
        browser = p.chromium.launch(headless=True)

        for year in range(2026, 1995, -1):
            try:
                get_movies_for_year(browser, year, writer)
                f.flush()
            except Exception as e:
                print(f"Error processing {year}: {e}")

        browser.close()

print(f"Movies written to {CSV_FILE}")