from playwright.sync_api import sync_playwright
import csv
import os

CSV_FILE = "movies.csv"

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

def get_movies_for_year(browser, year, writer):
    # page with all of the oscar nominations for best picture
    url = f"https://www.imdb.com/event/ev0000003/{year}/1/"
    page = browser.new_page()
    page.goto(url)

    try:
        # look for table of the best picture movies
        page.wait_for_selector('[data-testid="BestMotionPictureoftheYear"]', timeout=5000)
        category = page.locator('[data-testid="BestMotionPictureoftheYear"]')
    except:
        try:
            # the selector switches to BestPicture starting in 2004
            page.wait_for_selector('[data-testid="BestPicture"]', timeout=5000)
            category = page.locator('[data-testid="BestPicture"]')
        except:
            # error handling
            print(f"No best picture section found for {year}")
            page.close()
            return

    # find the links for each movie
    links = category.locator("a.ipc-title-link-wrapper:has(h3)")

    for i in range(links.count()):
        # get the link for the movie
        link = links.nth(i)

        # movie title
        title = link.locator("h3").inner_text()

        # link to go to movie page
        href = link.get_attribute("href")
        if not href or "/title/" not in href:
            continue
        full_url = "https://www.imdb.com" + href
        print(f"Processing {title} ({year})")
        
        # get critics choice info
        cc_result = get_critics_choice(browser, full_url)
        print(f"  Critics Choice Nominee: {cc_result['critics_choice_nom']}, Winner: {cc_result['critics_choice_win']}")

        # get bafta info
        bafta_result = get_bafta(browser, full_url)
        print(f"  BAFTA Nominee: {bafta_result['bafta_nom']}, Winner: {bafta_result['bafta_win']}")

        # get golden globes info
        gg_result = get_golden_globes(browser, full_url)
        print(f"  Golden Globes Nominee: {gg_result['golden_globes_nom']}, Winner: {gg_result['golden_globes_win']}")

        # get pga info
        pga_result = get_pga(browser, full_url)
        print(f"  PGA Nominee: {pga_result['pga_nom']}, Winner: {pga_result['pga_win']}")

        # get sag info
        sag_result = get_sag(browser, full_url)
        print(f"  SAG Nominee: {sag_result['sag_nom']}, Winner: {sag_result['sag_win']}")

        # add data to dictionary
        movie = {"title": title, "url": full_url, "year": year}
        movie.update(cc_result)
        movie.update(bafta_result)
        movie.update(gg_result)
        movie.update(pga_result)
        movie.update(sag_result)

        # Write each movie immediately to csv
        writer.writerow(movie)

    page.close()

# Main scraping loop
file_exists = os.path.exists(CSV_FILE)

# write all data to the csv
with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title","url","year","critics_choice_nom","critics_choice_win", "bafta_nom", "bafta_win",
                                           "golden_globes_nom", "golden_globes_win", "pga_nom", "pga_win", "sag_nom", "sag_win"])
    
    if f.tell() == 0:
        writer.writeheader()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        for year in range(2026, 1995, -1):
            try:
                get_movies_for_year(browser, year, writer)
                f.flush()  # ensures each year's movies are written
            except Exception as e:
                print(f"Error processing {year}: {e}")
        browser.close()

print(f"Movies written incrementally to {CSV_FILE}")