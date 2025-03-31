import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# Initialize session states
if 'trends_df' not in st.session_state:
    st.session_state.trends_df = None
if 'selected_trend' not in st.session_state:
    st.session_state.selected_trend = None
if 'tweet_text' not in st.session_state:
    st.session_state.tweet_text = None
if 'sentiment_scores' not in st.session_state:
    st.session_state.sentiment_scores = []

st.title("tweetX")
st.markdown("""
        <style>
        .main > div {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

gemini_api_key = st.text_input("Gemini API Key", type="password")

COUNTRY_CODES = {
    "Worldwide": "",
    "United States": "united-states",
    "United Kingdom": "united-kingdom",
    "India": "india",
    "Canada": "canada",
    "Australia": "australia",
    "Japan": "japan",
    "Germany": "germany",
    "France": "france",
    "Brazil": "brazil",
    "Spain": "spain",
    "Italy": "italy",
    "Netherlands": "netherlands",
    "South Korea": "south-korea",
    "Mexico": "mexico",
    "Argentina": "argentina",
    "Russia": "russia",
    "Turkey": "turkey",
    "Indonesia": "indonesia",
    "Saudi Arabia": "saudi-arabia",
    "Singapore": "singapore",
    "Thailand": "thailand",
    "Malaysia": "malaysia",
    "South Africa": "south-africa",
    "New Zealand": "new-zealand",
    "Ireland": "ireland",
    "Sweden": "sweden",
    "Norway": "norway",
    "Denmark": "denmark",
    "Finland": "finland"
}

def generate_tweet(prompt):
    """Generate tweet using Gemini AI"""
    if not gemini_api_key:
        st.error("Please enter your Gemini API Key")
        return None
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating tweet: {str(e)}")
        return None

def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(text)['compound']
    
    if sentiment_score >= 0.05:
        sentiment = "Positive"
    elif sentiment_score <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    return sentiment, sentiment_score

def fetch_twitter_trends(country_code=""):
    """Fetch current Twitter trends"""
    base_url = "https://trends24.in/"
    url = f"{base_url}{country_code}" if country_code else base_url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        trends = []
        trend_items = (
            soup.select(".trend-card__list li a") or
            soup.select("#trends-list li a") or
            soup.select(".trends-list li a")
        )
        
        if not trend_items:
            trend_items = soup.find_all('a', href=lambda x: x and 'hashtag' in x)
        
        for item in trend_items[:10]:
            name = item.get_text().strip()
            if not name:
                continue
                
            tweet_volume = "N/A"
            volume_element = item.parent.find('span', {'class': ['tweet-volume', 'volume']})
            if volume_element:
                volume_text = volume_element.get_text().strip()
                volume_text = volume_text.replace('K', '000').replace('+', '').replace(',', '')
                try:
                    tweet_volume = int(float(volume_text))
                except ValueError:
                    tweet_volume = volume_text
            
            trends.append({
                "Name": name,
                "Tweet Volume": tweet_volume
            })
        
        return pd.DataFrame(trends)
    
    except Exception as e:
        st.error(f"Error fetching trends: {str(e)}")
        return pd.DataFrame()

def generate_trend_based_tweet(trend_name, user_prompt=""):
    """Generate tweet based on trending topic"""
    prompt = f"""
    Write an engaging tweet about the trending topic "{trend_name}".
    Additional context from user: {user_prompt}
    
    Guidelines:
    - Keep it under 280 characters
    - Make it engaging and relevant
    - Include hashtags naturally
    - Consider the current context of why this topic is trending
    """
    return generate_tweet(prompt)

def plot_sentiment_trends():
    if st.session_state.sentiment_scores:
        df = pd.DataFrame(st.session_state.sentiment_scores, columns=["Sentiment Score"])
        st.subheader("Sentiment Trend")
        fig, ax = plt.subplots()
        df.plot(kind='line', ax=ax, marker='o', color='b')
        ax.set_ylabel("Sentiment Score")
        ax.set_xlabel("Tweet Number")
        ax.axhline(y=0.05, color='g', linestyle='--', label='Positive Threshold')
        ax.axhline(y=-0.05, color='r', linestyle='--', label='Negative Threshold')
        ax.legend()
        st.pyplot(fig)

def generate_word_cloud(trends_df):
    """Generate a word cloud from the trends DataFrame."""
    if trends_df is None or trends_df.empty:
        st.error("No trends available to generate a word cloud.")
        return

    # Combine all trend names into a single string
    trend_text = " ".join(trends_df["Name"].tolist())

    # Generate the word cloud
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(trend_text)

    # Display the word cloud
    st.subheader("Word Cloud of Trends")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)

# Main app layout
col1, col2 = st.columns([1, 1])

with col1:
    # Trend selection section
    country = st.selectbox("Select Country for Trends", options=list(COUNTRY_CODES.keys()))
    if st.button("Fetch Current Trends"):
        with st.spinner(f"Fetching trends for {country}..."):
            st.session_state.trends_df = fetch_twitter_trends(COUNTRY_CODES[country])
            if not st.session_state.trends_df.empty:
                st.session_state.selected_trend = st.session_state.trends_df["Name"].iloc[0]

    # Tweet generation section
    tweet_prompt = st.text_area("Enter additional context for the tweet (optional)")
    
    if st.session_state.trends_df is not None and not st.session_state.trends_df.empty:
        trends_list = st.session_state.trends_df["Name"].tolist()
        
        def on_trend_select():
            st.session_state.selected_trend = st.session_state.trend_selector
        
        selected_trend = st.selectbox(
            "Select a trend to tweet about",
            options=trends_list,
            key="trend_selector",
            on_change=on_trend_select,
            index=trends_list.index(st.session_state.selected_trend) if st.session_state.selected_trend in trends_list else 0
        )
        
        if st.button("Generate Tweet for Trend"):
            with st.spinner("Generating tweet..."):
                tweet = generate_trend_based_tweet(st.session_state.selected_trend, tweet_prompt)
                if tweet:
                    st.session_state.tweet_text = tweet

# Display section
with col2:
    if st.session_state.trends_df is not None:
        st.subheader(f"Current Trends - {country}")
        st.dataframe(st.session_state.trends_df)

if st.session_state.tweet_text:
        st.subheader("Generated Tweet")
        st.write(st.session_state.tweet_text)
        sentiment, score = analyze_sentiment(st.session_state.tweet_text)
        st.write(f"**Sentiment:** {sentiment} ({score:.2f})")
    
        st.session_state.sentiment_scores.append(score)
        plot_sentiment_trends()
        if st.button("Regenerate Tweet"):
            with st.spinner("Regenerating tweet..."):
                tweet = generate_trend_based_tweet(st.session_state.selected_trend, tweet_prompt)
                if tweet:
                    st.session_state.tweet_text = tweet
                    st.write("New Tweet:")
                    st.write(tweet)

# Add a button to generate the word cloud
if st.session_state.trends_df is not None and not st.session_state.trends_df.empty:
    if st.button("Generate Word Cloud"):
        generate_word_cloud(st.session_state.trends_df)
