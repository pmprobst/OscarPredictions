---
title: "Technical Report"
---

# Technical Report

## Executive Summary

This project examines whether Oscar Best Picture winners can be predicted using precursor award show results and the accumulated award histories of a film's cast. We scraped 30 years of IMDB data, covering every Best Picture nominee from 1996 through 2026, and trained a logistic regression model on features derived from five major precursor award shows (Golden Globes, SAG, PGA, Critics Choice, and BAFTA) alongside cast-level award totals computed up to the point of each film's Oscar nomination. The model was evaluated on a held-out test set and demonstrated meaningful predictive accuracy, confirming that award season momentum is a genuine signal for Best Picture outcomes.

## Project Context

The Oscar for Best Picture is the most prestigious award in the film industry, and predicting its winner has long been a subject of speculation among critics and industry insiders. Movie lovers believe that certain precursor award shows, particularly the Producers Guild and BAFTA, are strong leading indicators of Oscar success. Less explored is whether the accumulated prestige of a film's cast, measured through their prior award wins, adds additional predictive power beyond the precursor shows alone.

Our goal was to formalize this intuition into a reproducible data pipeline and quantitative model. A successful outcome means building a Python package that scrapes, processes, and models this data end-to-end, and that produces predictions interpretable enough to evaluate which features matter most.

## Data Sources

- **Oscar nominees:** IMDB event pages for the Academy Awards, cycling through ceremony years from 1996 to 2026. Each page lists the Best Picture nominees and links to their individual IMDB film pages.
- **Precursor award data:** IMDB awards pages for each nominated film, recording nominations and wins at the Golden Globe Awards, Screen Actors Guild (SAG) Awards, Producers Guild of America (PGA) Awards, Critics Choice Awards, and BAFTA.
- **Cast award histories:** IMDB filmography and awards pages for each cast member of each nominated film. Only awards won prior to the year of that film's Oscar nomination were counted, preventing any data leakage from future accolades.

All data was scraped from publicly accessible IMDB pages using Playwright. The bundled base dataset covering 1996–2023 is included with the package.

## Methodology

**1. Data Acquisition**

We built a multi-stage scraping pipeline using Playwright to automate browser interactions with IMDB. The pipeline first scrapes the list of Best Picture nominees for each ceremony year, then visits each film's IMDB page to collect precursor award results, then scrapes the full cast list for each film, and finally retrieves the individual award history for each cast member.

**2. Feature Engineering**

From the raw scraped data we engineered three layers of features. First, we built an actor-year award matrix recording how many awards each actor had won by each calendar year. Second, we summed those per-actor totals across each film's full cast to produce film-level cast award aggregates. Third, we joined those cast totals to the film-level precursor award data to produce the final modeling dataset, with one row per nominated film per year and a binary target indicating whether that film won Best Picture.

**3. Modeling**

We trained a logistic regression model using scikit-learn with varying year stratified train/test splits. Logistic regression was chosen for its interpretability: the model coefficients directly indicate which features most strongly predict a win.

## Results

The model was evaluated on the held-out test set using accuracy by examining per-year predicted vs. actual winners to understand where the model succeeded and where it did not.

### Model Performance

| Train Size | Test | Accuracy|
|---|---|---|
| 25 | 5 | 100% |
| 20 | 10 | 81.8% |
| 15 | 15 | 81.2% |

### Feature Importance

The logistic regression coefficients reveal which features most strongly predicted a Best Picture win. Positive coefficients indicate that higher values of that feature increased the predicted probability of winning.

| Feature | Coefficient |
|---|---|
| sag_nom | 0.793 |
| bafta_nom | 0.734 |
| cast_dga_wins_total | 0.639 |
| pga_winrate | 0.605 |
| pga_win | 0.605 |

## Discussion

Our analysis shows that precursor award show results and cast award histories together provide meaningful signal for predicting the Oscar Best Picture winner. The model correctly consistently identified the winner about 81% of the time, a strong result that confirms award season momentum is genuinely predictive of Best Picture outcomes.

The strongest positive predictors were SAG nominations, BAFTA nominations, and cast DGA wins, suggesting that films recognized by the acting and directing guilds early in the season carry a significant advantage. PGA win rate and outright PGA wins were also among the top predictors, consistent with the consensus among movie lovers that the Producers Guild is one of the most reliable leading indicators of Oscar success. Interestingly, cast-level features such as total Oscar wins, total acting wins, and total DGA wins among a film's cast, ranked among the top predictors alongside the precursor shows, confirming that cast prestige adds real predictive power beyond precursor results alone.


## Limitations

- **Multicollinearity:** Several features in our dataset are highly correlated with one another — for example, a film that wins the PGA is obviously going to be nominated for PGA, and a film with a decorated cast is likely to appear at multiple precursor shows. This makes it difficult for the model to isolate the unique effect of any single feature. The negative coefficients on some features such as BAFTA wins and PGA nominations are likely a symptom of this: there is no logical reason that winning BAFTA should hurt a film's Oscar chances. Rather, the model is picking up on correlations between features rather than true causal relationships, and the coefficients should be interpreted with caution.

- **Class imbalance:** Out of every group of Best Picture nominees, exactly one film wins each year. This means that in any given year, roughly 80–90% of the rows in our dataset are losses and only one is a win. With such a skewed target variable, the model has very few positive examples to learn from relative to the number of negative ones, which can make it harder to distinguish a true winner from a strong runner-up. This is a fundamental constraint of the problem rather than a flaw in our approach, but it does limit how confidently the model can assign win probabilities.

## Future Work

- Incorporate additional features such as Metacritic and Rotten Tomatoes scores, box office gross, and genre classifications.
- Address multicollinearity and class imbalance to provide a clearer picture of the actual impact of precursor wins and nominations