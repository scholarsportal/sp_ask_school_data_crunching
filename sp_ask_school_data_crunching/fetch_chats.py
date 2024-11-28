from datetime import datetime, timedelta
import lh3.api
from typing import List, Dict, Any

def get_chats_between_dates(start_date: str, end_date: str) -> List[Dict[Any, Any]]:
    """
    Get chats between two dates using LibraryH3lp API
    
    Args:
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
                all_chats.extend(daily_chats)
                print(f"Fetched {len(daily_chats)} chats for {current_date.date()}")
                
        except Exception as e:
            print(f"Error fetching data for {current_date.date()}: {str(e)}")
            
        # Move to next day
        current_date += timedelta(days=1)
    
    print(f"\nTotal chats fetched: {len(all_chats)}")
    return all_chats

if __name__ == "__main__":
    # Example usage when running script directly
    chats = get_chats_between_dates("2016-11-25", "2024-12-01")
    print(f"\nAnalysis:")
    print(f"Total chats: {len(chats)}")