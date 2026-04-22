import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

movies = pd.read_csv('movies.csv')
movies['era'] = movies['year'].apply(lambda x: 'post_2010' if x >= 2010 else 'pre_2010')
precursors = ['critics_choice', 'bafta', 'golden_globes', 'pga', 'sag']
nom_cols = [f'{p}_nom' for p in precursors]
win_cols = [f'{p}_win' for p in precursors]
movies['precursor_wins'] = movies[win_cols].sum(axis=1)

st.title('Oscar Best Picture EDA')

# Sidebar controls
with st.sidebar:
    st.header('Filters')

    year_range = st.slider('Year Range',
                           min_value=int(movies['year'].min()),
                           max_value=int(movies['year'].max()),
                           value=(int(movies['year'].min()), int(movies['year'].max())))

    selected_precursors = st.multiselect('Precursors to Include',
                                         precursors,
                                         default=precursors,
                                         format_func=lambda x: x.replace('_', ' ').title())

    era_filter = st.radio('Era', ['All', 'Pre-2010', 'Post-2010'])

    selected_film = st.selectbox('Look Up a Film', [''] + sorted(movies['title'].tolist()))

# Apply filters
filtered = movies[movies['year'].between(year_range[0], year_range[1])]

if era_filter == 'Pre-2010':
    filtered = filtered[filtered['era'] == 'pre_2010']
elif era_filter == 'Post-2010':
    filtered = filtered[filtered['era'] == 'post_2010']

sel_nom_cols = [f'{p}_nom' for p in selected_precursors]
sel_win_cols = [f'{p}_win' for p in selected_precursors]
filtered['precursor_wins'] = filtered[sel_win_cols].sum(axis=1)

# Film lookup
if selected_film:
    st.subheader(f'Film Lookup: {selected_film}')
    film_data = movies[movies['title'] == selected_film]
    st.dataframe(film_data)
    st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    'Overview',
    'Base Rates',
    'Precursor Predictiveness',
    'Sweep Analysis',
    'Era Comparison'
])

with tab1:
    st.header('Dataset Overview')
    st.write(f'Showing **{len(filtered)}** films from **{year_range[0]}** to **{year_range[1]}**')
    st.dataframe(filtered)

    fig, ax = plt.subplots(figsize=(12, 4))
    nominees_per_year = filtered.groupby('year').size()
    ax.bar(nominees_per_year.index, nominees_per_year.values)
    ax.axvline(x=2010, color='red', linestyle='--', label='Expansion (2010)')
    ax.set_title('Nominees per Year')
    ax.set_xlabel('Year')
    ax.set_ylabel('Number of Nominees')
    ax.legend()
    st.pyplot(fig)

with tab2:
    st.header('Base Rates')
    st.write('Of all films nominated for Best Picture, what fraction also appeared at each precursor show?')

    if not selected_precursors:
        st.warning('Select at least one precursor in the sidebar.')
    else:
        base_rates = pd.DataFrame({
            'nom_rate': filtered[sel_nom_cols].mean().values,
            'win_rate': filtered[sel_win_cols].mean().values
        }, index=selected_precursors)

        fig, ax = plt.subplots(figsize=(10, 4))
        base_rates.plot(kind='bar', ax=ax)
        ax.set_title('Nomination and Win Rates Across Precursors')
        ax.set_ylabel('Rate (among all nominees)')
        ax.set_xticklabels([p.replace('_', ' ').title() for p in selected_precursors], rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

with tab3:
    st.header('Precursor Predictiveness')
    st.write('Of all films that won each precursor, what fraction went on to win the Oscar?')

    if not selected_precursors:
        st.warning('Select at least one precursor in the sidebar.')
    else:
        oscar_win_rates = {}
        for p in selected_precursors:
            rates = filtered.groupby(f'{p}_win')['oscar_win'].mean()
            oscar_win_rates[p] = {
                'Did Not Win Precursor': rates.get(0, 0),
                'Won Precursor': rates.get(1, 0)
            }
        rates_movies = pd.DataFrame(oscar_win_rates).T
        rates_movies.index = [p.replace('_', ' ').title() for p in selected_precursors]

        fig, ax = plt.subplots(figsize=(10, 4))
        rates_movies.plot(kind='bar', ax=ax)
        ax.set_title('Oscar Win Rate by Precursor Win')
        ax.set_ylabel('Oscar Win Rate')
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

with tab4:
    st.header('Sweep Analysis')
    st.write('Does winning more precursors make you more likely to win the Oscar?')

    sweep_rates = filtered.groupby('precursor_wins')['oscar_win'].mean().reset_index()
    sweep_counts = filtered.groupby('precursor_wins').size().reset_index(name='count')
    sweep = sweep_rates.merge(sweep_counts, on='precursor_wins')

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.bar(sweep['precursor_wins'], sweep['oscar_win'], alpha=0.6, label='Oscar Win Rate')
    ax2.plot(sweep['precursor_wins'], sweep['count'], color='red', marker='o', label='# of Films')
    ax1.set_xlabel('Number of Precursor Awards Won')
    ax1.set_ylabel('Oscar Win Rate')
    ax2.set_ylabel('Number of Films')
    ax1.set_title('Oscar Win Rate by Number of Precursors Won')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
    plt.tight_layout()
    st.pyplot(fig)

with tab5:
    st.header('Era Comparison')
    st.write('Has each precursor become more or less predictive since the 2010 expansion?')

    if era_filter != 'All':
        st.warning('Era Comparison works best with "All" selected in the sidebar — showing both eras.')

    results = []
    for p in selected_precursors:
        for era, era_df in filtered.groupby('era'):
            precursor_winners = era_df[era_df[f'{p}_win'] == 1]
            total_years = era_df['year'].nunique()
            correct_years = precursor_winners.groupby('year')['oscar_win'].max().sum()
            results.append({
                'precursor': p.replace('_', ' ').title(),
                'era': era,
                'correct_years': int(correct_years),
                'total_years': total_years,
                'pct_correct': correct_years / total_years if total_years > 0 else 0
            })

    if not results:
        st.warning('No data available for the current filters.')
    else:
        results_df = pd.DataFrame(results)
        precursor_labels = [p.replace('_', ' ').title() for p in selected_precursors]
        pre = results_df[results_df['era'] == 'pre_2010'].set_index('precursor')
        post = results_df[results_df['era'] == 'post_2010'].set_index('precursor')

        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(selected_precursors))
        width = 0.35
        bars1 = ax.bar([i - width/2 for i in x], [pre.loc[p, 'pct_correct'] if p in pre.index else 0 for p in precursor_labels], width, label='Pre-2010', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], [post.loc[p, 'pct_correct'] if p in post.index else 0 for p in precursor_labels], width, label='Post-2010', alpha=0.8)

        for bars, era_df in zip([bars1, bars2], [pre, post]):
            for bar, p in zip(bars, precursor_labels):
                if p in era_df.index:
                    correct = int(era_df.loc[p, 'correct_years'])
                    total = int(era_df.loc[p, 'total_years'])
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                            f'{correct}/{total}', ha='center', va='bottom', fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(precursor_labels, rotation=45)
        ax.set_ylabel('% of Years Correctly Predicted Oscar Winner')
        ax.set_title('Precursor Predictiveness Pre vs Post 2010 Expansion')
        ax.set_ylim(0, 1.2)
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)