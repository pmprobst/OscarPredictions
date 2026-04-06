import re
from dataclasses import dataclass

CSV_FILE = "movies.csv"
CAST_CSV_FILE = "film_actors.csv"
CAST_FIELDNAMES = ["year", "film_title", "actor_name", "actor_imdb_url"]
ACTOR_AWARDS_CSV_FILE = "actor_awards.csv"
ACTOR_AWARD_FIELDNAMES = ["actor_name", "actor_imdb_url", "award", "year", "outcome"]
NO_AWARD_ACTORS_CSV_FILE = "no_award_actors.csv"
NO_AWARD_ACTORS_FIELDNAMES = ["actor_name", "actor_imdb_url"]


@dataclass(frozen=True)
class AwardScrapeResult:
    """Result of scraping one person's IMDb awards page."""

    rows: list[dict]
    ok: bool
    """True if the page was loaded and parsed; False on missing nm id or scrape errors."""


def _normalize_actor_name(name: str) -> str:
    """Strip IMDb accessibility prefix from link visible text."""
    s = re.sub(r"\s+", " ", (name or "").strip())
    return re.sub(r"^go to\s+", "", s, flags=re.IGNORECASE).strip()


def _imdb_name_abs_url(href: str) -> str:
    if not href:
        return ""
    path = href.split("?")[0]
    if path.startswith("http"):
        return path
    if path.startswith("/"):
        return "https://www.imdb.com" + path
    return "https://www.imdb.com/" + path
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


def nm_id_from_profile_url(url: str) -> str | None:
    """IMDb person id (nm……) from a profile or /name/nm…… URL."""
    m = re.search(r"/name/(nm\d+)", (url or "").split("?")[0], re.I)
    return m.group(1) if m else None


def extract_person_award_rows(
    browser, actor_imdb_url: str, actor_name: str
) -> AwardScrapeResult:
    """
    Scrape all nomination/win lines from a person's IMDb awards page (/name/nm…/awards/).

    Navigates directly to the awards URL (same end state as the Awards tab). Each row uses
    the maximum 4-digit year found in the line as ``year`` (ceremony / credit-year heuristic
    when multiple years appear). ``outcome`` is ``won`` or ``nominated``.

    On success (including zero matching award lines), ``ok`` is True. On missing nm id or
    navigation/parsing failure, ``ok`` is False and ``rows`` is empty.
    """
    nm = nm_id_from_profile_url(actor_imdb_url)
    if not nm:
        return AwardScrapeResult([], False)
    canonical_url = f"https://www.imdb.com/name/{nm}/"
    page = None
    try:
        page = browser.new_page()
        awards_url = f"https://www.imdb.com/name/{nm}/awards/"
        page.goto(awards_url, timeout=90000, wait_until="load")
        page.wait_for_selector("body", timeout=60000)
        try:
            page.wait_for_function(
                "() => document.querySelector('main') && document.querySelectorAll('main li').length > 0",
                timeout=25000,
            )
        except Exception:
            pass

        items = page.locator("main li")
        if items.count() == 0:
            items = page.locator("li")

        rows_out: list[dict] = []
        for i in range(items.count()):
            item = items.nth(i)
            text = item.inner_text()
            if "Nominee" not in text and "Winner" not in text:
                continue
            years = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", text)]
            if not years:
                continue
            year = max(years)
            outcome = "won" if "Winner" in text else "nominated"
            try:
                award = item.evaluate(
                    """(el) => {
                      let prefix = '';
                      const section = el.closest('section');
                      if (section) {
                        const h = section.querySelector('h1, h2, h3, h4, .ipc-title__text');
                        if (h) {
                          const t = (h.textContent || '').replace(/\\s+/g, ' ').trim();
                          if (t) prefix = t + ' — ';
                        }
                      }
                      return prefix + (el.innerText || '').replace(/\\s+/g, ' ').trim();
                    }"""
                )
            except Exception:
                award = re.sub(r"\s+", " ", text).strip()
            rows_out.append(
                {
                    "actor_name": actor_name,
                    "actor_imdb_url": canonical_url,
                    "award": award,
                    "year": year,
                    "outcome": outcome,
                }
            )
        return AwardScrapeResult(rows_out, True)
    except Exception:
        return AwardScrapeResult([], False)
    finally:
        if page is not None:
            page.close()


def _pairs_from_name_links(links):
    seen_nm = set()
    pairs = []
    for i in range(links.count()):
        a = links.nth(i)
        href = a.get_attribute("href") or ""
        m = re.search(r"/name/(nm\d+)", href)
        if not m:
            continue
        nm = m.group(1)
        if nm in seen_nm:
            continue
        seen_nm.add(nm)
        name = _normalize_actor_name(a.inner_text())
        if not name or len(name) > 200:
            continue
        pairs.append(
            {"nm": nm, "name": name, "url": _imdb_name_abs_url(href)}
        )
    return pairs


def _pull_cast_pairs_from_fullcredits_dom(page):
    """
    Parse only the Cast block on /fullcredits/. Match the section titled \"Cast\" (not
    \"Full cast & crew\" page chrome); cast may be div-based (no tables in main). Sibling
    walk after the Cast heading collects nm links until the next department heading.
    """
    return page.evaluate(
        r"""() => {
          const seen = new Set();
          const rows = [];
          function normName(s) {
            return (s || "").replace(/\s+/g, " ").trim();
          }
          function stripGoTo(s) {
            return normName(s).replace(/^go to\s+/i, "");
          }
          function absImdbNameUrl(href) {
            const path = (href || "").split("?")[0];
            if (!path) return "";
            if (/^https?:\/\//i.test(path)) return path;
            const p = path.startsWith("/") ? path : "/" + path;
            return "https://www.imdb.com" + p;
          }
          function addFromRoot(root) {
            if (!root) return;
            root.querySelectorAll('a[href*="/name/nm"]').forEach((a) => {
              const href = a.getAttribute("href") || "";
              const m = href.match(/\/name\/(nm\d+)/);
              if (!m) return;
              const nm = m[1];
              if (seen.has(nm)) return;
              let name = stripGoTo(a.innerText || a.textContent);
              if (!name) {
                const t = a.getAttribute("title") || a.getAttribute("aria-label");
                name = stripGoTo(t);
              }
              if (!name || name.length > 200) return;
              seen.add(nm);
              rows.push({
                nm: nm,
                name: name,
                url: absImdbNameUrl(href),
              });
            });
          }
          function headingIsCast(el) {
            const t = normName(el && el.textContent);
            if (!t || /^casting\b/i.test(t)) return false;
            if (/full cast/i.test(t)) return false;
            return /^cast\b/i.test(t);
          }
          function isCastSubOrNoise(el) {
            const t = normName(el && el.textContent);
            if (!t) return true;
            if (/credits order|verified as complete|^in$/i.test(t)) return true;
            if (/uncredited|rest of cast|alphabetical/i.test(t)) return true;
            return false;
          }
          function isNewDepartmentHeading(el) {
            if (!el || !el.matches) return false;
            if (!el.matches("h1, h2, h3, h4, h5, h6")) return false;
            if (headingIsCast(el)) return false;
            if (isCastSubOrNoise(el)) return false;
            const t = normName(el.textContent);
            if (t.length < 2 || t.length >= 120) return false;
            if (/^writer/i.test(t)) return true;
            if (/produced by|directed by|music|sound|camera|editorial|casting/i.test(t))
              return true;
            return true;
          }
          function addCastBlockAfterHeading(hCast) {
            let el = hCast.nextElementSibling;
            let steps = 0;
            while (el && steps++ < 100) {
              if (isNewDepartmentHeading(el)) break;
              if (el.tagName === "TABLE") {
                addFromRoot(el);
              } else {
                const tbls = el.querySelectorAll && el.querySelectorAll("table");
                if (tbls && tbls.length) {
                  tbls.forEach((t) => addFromRoot(t));
                } else {
                  addFromRoot(el);
                }
              }
              el = el.nextElementSibling;
            }
          }
          let table = document.querySelector("table.cast_list");
          if (table) {
            addFromRoot(table);
            if (rows.length) return rows;
          }
          const main = document.querySelector("main");
          if (!main) return rows;
          const sectionEls = main.querySelectorAll(
            "section, div.ipc-page-section, div[class*='PageSection']"
          );
          for (const sec of sectionEls) {
            const hx = sec.querySelector(
              "h1, h2, h3, h4, h5, h6, .ipc-title__text, [class*='TitleText']"
            );
            if (!hx || !headingIsCast(hx)) continue;
            addFromRoot(sec);
            if (rows.length) return rows;
          }
          const heads = Array.from(
            main.querySelectorAll("h1, h2, h3, h4, h5, h6")
          );
          const hCast = heads.find(headingIsCast);
          if (hCast) {
            addCastBlockAfterHeading(hCast);
            if (rows.length) return rows;
          }
          const castSection = main.querySelector('[data-testid*="cast"]');
          if (castSection) {
            const hh = castSection.querySelector("h1, h2, h3, h4, h5, h6");
            if (hh && headingIsCast(hh)) addCastBlockAfterHeading(hh);
            else addFromRoot(castSection);
            if (rows.length) return rows;
          }
          return rows;
        }"""
    )


def extract_film_actor_rows(browser, movie_url, year, film_title):
    """
    Film–actor pairs from IMDb full credits: `goto .../fullcredits/` and parse the Cast table
    in-page. Fallback: open title page, click Top Cast → fullcredits, parse again.
    """
    page = browser.new_page()
    try:
        base = movie_url.split("?")[0].rstrip("/")
        if re.search(r"/fullcredits/?$", base, re.I):
            fullcredits_url = base + "/" if not base.endswith("/") else base
        else:
            fullcredits_url = base + "/fullcredits/"

        page.goto(fullcredits_url, timeout=90000, wait_until="load")
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('a[href*=\"/name/nm\"]').length > 0",
                timeout=45000,
            )
        except Exception:
            pass

        pairs = _pull_cast_pairs_from_fullcredits_dom(page)

        if not pairs:
            page.goto(base, timeout=90000, wait_until="load")
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-testid]').length > 0",
                    timeout=45000,
                )
            except Exception:
                pass
            top_name_re = re.compile(r"top cast\s+\d+\+?", re.IGNORECASE)
            top_hdr = page.locator(
                'section[data-testid="title-cast"] a.ipc-title-link-wrapper[href*="fullcredits"]'
            )
            try:
                if top_hdr.count() > 0:
                    top_hdr.first.wait_for(state="visible", timeout=20000)
                    top_hdr.first.click()
                    try:
                        page.wait_for_load_state("load", timeout=90000)
                    except Exception:
                        pass
                else:
                    top_cast = page.get_by_role("link", name=top_name_re)
                    if top_cast.count() == 0:
                        top_cast = page.get_by_role("button", name=top_name_re)
                    if top_cast.count() > 0:
                        top_cast.first.click()
                        try:
                            page.wait_for_load_state("load", timeout=90000)
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                cast_tab = page.get_by_role("link", name="Cast", exact=True)
                if cast_tab.count() == 0:
                    cast_tab = page.get_by_role("tab", name="Cast", exact=True)
                if cast_tab.count() == 0:
                    cast_tab = page.get_by_role("button", name="Cast", exact=True)
                if cast_tab.count() > 0:
                    cast_tab.first.click()
            except Exception:
                pass

            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('a[href*=\"/name/nm\"]').length > 0",
                    timeout=25000,
                )
            except Exception:
                pass

            pairs = _pull_cast_pairs_from_fullcredits_dom(page)

        if not pairs and "fullcredits" not in (page.url or ""):
            links = page.locator('[data-testid="title-cast-item"] a[href*="/name/nm"]')
            if links.count() == 0:
                links = page.locator('[data-testid="title-cast"] a[href*="/name/nm"]')
            pairs = _pairs_from_name_links(links)

        return [
            {
                "year": year,
                "film_title": film_title,
                "actor_name": _normalize_actor_name(p["name"]),
                "actor_imdb_url": p.get("url")
                or f"https://www.imdb.com/name/{p['nm']}/",
            }
            for p in pairs
        ]
    except Exception:
        return []
    finally:
        page.close()


def iter_best_picture_nominees(browser, year, max_movies=None):
    """
    Yield (title, full_imdb_url, year) for each Best Picture nominee on the ceremony page.
    browser: Playwright BrowserContext.
    """
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
        movies_done = 0
        for i in range(links.count()):
            link = links.nth(i)
            title = link.locator("h3").inner_text()
            href = link.get_attribute("href")
            if not href or "/title/" not in href:
                continue
            full_url = "https://www.imdb.com" + href
            yield title, full_url, year
            movies_done += 1
            if max_movies is not None and movies_done >= max_movies:
                break
    finally:
        page.close()


def get_movies_for_year(browser, year, writer, cast_writer=None, max_movies=None):
    """Scrape awards + director counts per nominee; optionally write cast CSV rows."""
    for title, full_url, y in iter_best_picture_nominees(browser, year, max_movies):
        print(f"Processing {title} ({y})")

        if cast_writer:
            for cast_row in extract_film_actor_rows(browser, full_url, y, title):
                cast_writer.writerow(cast_row)

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

        director_awards = get_director_award_counts(browser, full_url, y)
        print(
            f"  Director awards (through {y}): noms={director_awards['director_award_noms']}, wins={director_awards['director_award_wins']}"
        )

        movie = {"title": title, "url": full_url, "year": y}
        movie.update(cc_result)
        movie.update(bafta_result)
        movie.update(gg_result)
        movie.update(pga_result)
        movie.update(sag_result)
        movie.update(director_awards)

        writer.writerow(movie)


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