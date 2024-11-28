from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import lh3.api
from typing import List, Dict, Any

def get_school_chats_histogram(school_queue: str, start_date: str, end_date: str):
    """
    Create a histogram of chats for a specific school queue between two dates
    
    Args:
        school_queue: Queue name (e.g., 'toronto-st-george')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    # Initialize client
    client = lh3.api.Client()
    
    # Convert strings to datetime objects
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    all_chats = []
    current_date = start_dt
    
    while current_date <= end_dt:
        try:
            # Get chats for current day
            daily_chats = client.chats().list_day(
                current_date.year,
                current_date.month,
                current_date.day
            )
            
            if daily_chats:
                # Filter chats for specific queue
                queue_chats = [
                    chat for chat in daily_chats 
                    if chat['queue'] == school_queue
                ]
                all_chats.extend(queue_chats)
                print(f"Fetched {len(queue_chats)} chats for {current_date.date()}")
                
        except Exception as e:
            print(f"Error fetching data for {current_date.date()}: {str(e)}")
            
        # Move to next day
        current_date += timedelta(days=1)
    
    print(f"\nTotal chats fetched for {school_queue}: {len(all_chats)}")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_chats)
    
    # Convert started time to datetime
    df['started'] = pd.to_datetime(df['started'])
    
    # Create monthly counts
    monthly_counts = df.groupby(df['started'].dt.to_period('M')).size().reset_index()
    monthly_counts.columns = ['Month', 'Number of Chats']
    monthly_counts['Month'] = monthly_counts['Month'].astype(str)
    
    # Create histogram using plotly
    fig = px.bar(
        monthly_counts, 
        x='Month', 
        y='Number of Chats',
        title=f'Monthly Chat Distribution for {school_queue}\n{start_date} to {end_date}',
        labels={'Month': 'Month', 'Number of Chats': 'Number of Chats'},
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        bargap=0.1
    )
    
    # Save the plot as HTML
    output_file = f"{school_queue}_histogram_{start_date}_to_{end_date}.html"
    fig.write_html(output_file)
    print(f"\nHistogram saved as {output_file}")
    
    # Return the DataFrame for additional analysis
    return df

if __name__ == "__main__":
    # Example usage
    df = get_school_chats_histogram(
        school_queue="toronto-st-george",
        start_date="2018-01-01",
        end_date="2020-05-31"
    )
    
    # Print some basic statistics
    print("\nBasic Statistics:")
    print(f"Average chat duration: {df['duration'].mean():.2f} seconds")
    print(f"Median wait time: {df['wait'].median():.2f} seconds")
    print(f"Total number of unique operators: {df['operator'].nunique()}")