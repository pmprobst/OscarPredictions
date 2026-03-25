from playwright.sync_api import sync_playwright
import csv

def get_critics_choice(browser, movie_url):
    page = browser.new_page()
    try:
        awards_url = movie_url.split("?")[0] + "awards/"
        page.goto(awards_url, timeout=60000)
        page.wait_for_selector("body")

        # jump to Critics Choice Awards section
        try:
            page.get_by_label("Jump to").select_option("#ev0000133")
            page.wait_for_timeout(1000)
        except:
            return {"critics_choice_nom": 0, "critics_choice_win": 0}

        items = page.locator("li")
        nom = 0
        win = 0

        for i in range(items.count()):
            text = items.nth(i).inner_text()
            if "Critics Choice Award" in text and "Best Picture" in text:
                if "Nominee" in text:
                    nom = 1
                if "Winner" in text:
                    win = 1
                    nom = 1

        return {"critics_choice_nom": nom, "critics_choice_win": win}

    except:
        return {"critics_choice_nom": 0, "critics_choice_win": 0}

    finally:
        page.close()


def get_movies_for_year(browser, year):
    url = f"https://www.imdb.com/event/ev0000003/{year}/1/"
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector('[data-testid="BestMotionPictureoftheYear"]')

    category = page.locator('[data-testid="BestMotionPictureoftheYear"]')
    links = category.locator("a.ipc-title-link-wrapper:has(h3)")

    movies = []

    for i in range(links.count()):
        link = links.nth(i)
        title = link.locator("h3").inner_text()
        href = link.get_attribute("href")
        if not href or "/title/" not in href:
            continue
        full_url = "https://www.imdb.com" + href
        print(f"Processing {title} ({year})")

        result = get_critics_choice(browser, full_url)
        
        # 🔹 Print the nomination and win results immediately
        print(f"  Critics Choice Nominee: {result['critics_choice_nom']}, Winner: {result['critics_choice_win']}")

        movie = {"title": title, "url": full_url, "year": year}
        movie.update(result)

        movies.append(movie)

    page.close()
    return movies


all_movies = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    for year in range(2026, 1995, -1):  # 2026 down to 1996
        year_movies = get_movies_for_year(browser, year)
        all_movies.extend(year_movies)

    browser.close()

# Write all data to CSV
if all_movies:
    headers = all_movies[0].keys()
    with open("movies_1996_2026.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_movies)

    print(f"Saved {len(all_movies)} movies to movies_1996_2026.csv")