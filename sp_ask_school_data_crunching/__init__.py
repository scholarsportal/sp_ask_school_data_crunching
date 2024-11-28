from .fetch_chats import get_chats_between_dates

__version__ = "0.1.0"

__all__ = ["get_chats_between_dates"]


from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import lh3.api
from typing import List, Dict, Any, Tuple

class ChatAnalytics:
    def __init__(self, school_queue: str, start_date: str, end_date: str):
        """Initialize ChatAnalytics with school and date range"""
        self.school_queue = school_queue
        self.start_date = start_date
        self.end_date = end_date
        self.df = self._fetch_data()
        
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch and prepare chat data"""
        client = lh3.api.Client()
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
        
        all_chats = []
        current_date = start_dt
        
        while current_date <= end_dt:
            try:
                daily_chats = client.chats().list_day(
                    current_date.year,
                    current_date.month,
                    current_date.day
                )
                
                if daily_chats:
                    queue_chats = [
                        chat for chat in daily_chats 
                        if chat['queue'] == self.school_queue
                    ]
                    all_chats.extend(queue_chats)
                    print(f"Fetched {len(queue_chats)} chats for {current_date.date()}")
                    
            except Exception as e:
                print(f"Error fetching data for {current_date.date()}: {str(e)}")
                
            current_date += timedelta(days=1)
        
        df = pd.DataFrame(all_chats)
        df['started'] = pd.to_datetime(df['started'])
        df['accepted'] = pd.to_datetime(df['accepted'])
        df['ended'] = pd.to_datetime(df['ended'])
        
        # Add derived columns
        df['hour'] = df['started'].dt.hour
        df['day_of_week'] = df['started'].dt.day_name()
        df['month'] = df['started'].dt.to_period('M')
        
        return df

    def create_monthly_histogram(self) -> go.Figure:
        """Create monthly chat distribution histogram"""
        monthly_counts = self.df.groupby('month').size().reset_index()
        monthly_counts.columns = ['Month', 'Number of Chats']
        monthly_counts['Month'] = monthly_counts['Month'].astype(str)
        
        fig = px.bar(
            monthly_counts,
            x='Month',
            y='Number of Chats',
            title=f'Monthly Chat Distribution for {self.school_queue}',
        )
        fig.update_layout(xaxis_tickangle=-45)
        return fig

    def create_hourly_heatmap(self) -> go.Figure:
        """Create hourly chat distribution heatmap"""
        hourly_by_day = pd.crosstab(
            self.df['day_of_week'],
            self.df['hour']
        )
        
        # Reorder days of week
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hourly_by_day = hourly_by_day.reindex(days_order)
        
        fig = px.imshow(
            hourly_by_day,
            title='Chat Activity Heatmap by Hour and Day',
            labels=dict(x='Hour of Day', y='Day of Week', color='Number of Chats'),
            aspect='auto'
        )
        return fig

    def create_operator_workload(self) -> go.Figure:
        """Create operator workload visualization"""
        operator_stats = self.df.groupby('operator').agg({
            'id': 'count',
            'duration': 'mean',
            'wait': 'mean'
        }).reset_index()
        
        operator_stats.columns = ['Operator', 'Total Chats', 'Avg Duration', 'Avg Wait']
        operator_stats = operator_stats.sort_values('Total Chats', ascending=True)
        
        fig = make_subplots(rows=1, cols=2, 
                          subplot_titles=('Total Chats by Operator', 
                                        'Average Chat Duration by Operator'))
        
        fig.add_trace(
            go.Bar(x=operator_stats['Total Chats'], 
                  y=operator_stats['Operator'], 
                  orientation='h',
                  name='Total Chats'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=operator_stats['Avg Duration'], 
                  y=operator_stats['Operator'], 
                  orientation='h',
                  name='Avg Duration'),
            row=1, col=2
        )
        
        fig.update_layout(height=max(400, len(operator_stats) * 20),
                         title_text=f"Operator Workload Analysis for {self.school_queue}")
        return fig

    def generate_statistics(self) -> Dict:
        """Generate comprehensive statistics"""
        stats = {
            'Total Chats': len(self.df),
            'Date Range': f"{self.start_date} to {self.end_date}",
            'Unique Operators': self.df['operator'].nunique(),
            'Average Duration (minutes)': self.df['duration'].mean() / 60,
            'Median Wait Time (seconds)': self.df['wait'].median(),
            'Peak Hour': self.df.groupby('hour')['id'].count().idxmax(),
            'Busiest Day': self.df['day_of_week'].mode()[0],
            'Average Chats per Day': len(self.df) / self.df['started'].dt.date.nunique(),
            'Peak Month': self.df.groupby('month').size().idxmax().strftime('%Y-%m'),
        }
        return stats

    def save_all_visualizations(self, output_prefix: str = "chat_analysis"):
        """Save all visualizations to HTML files"""
        # Monthly histogram
        self.create_monthly_histogram().write_html(f"{output_prefix}_monthly.html")
        
        # Hourly heatmap
        self.create_hourly_heatmap().write_html(f"{output_prefix}_heatmap.html")
        
        # Operator workload
        self.create_operator_workload().write_html(f"{output_prefix}_operators.html")
        
        # Create a combined dashboard
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Monthly Distribution', 'Daily Heatmap', 'Operator Workload'),
            vertical_spacing=0.1,
            specs=[[{"type": "bar"}],
                  [{"type": "heatmap"}],
                  [{"type": "bar"}]]
        )
        
        # Add all plots to the dashboard
        monthly_fig = self.create_monthly_histogram()
        heatmap_fig = self.create_hourly_heatmap()
        operator_fig = self.create_operator_workload()
        
        # Combine plots
        fig.add_trace(monthly_fig.data[0], row=1, col=1)
        fig.add_trace(heatmap_fig.data[0], row=2, col=1)
        fig.add_trace(operator_fig.data[0], row=3, col=1)
        
        fig.update_layout(height=1500, title_text=f"Chat Analysis Dashboard for {self.school_queue}")
        fig.write_html(f"{output_prefix}_dashboard.html")

def analyze_school_chats(school_queue: str, start_date: str, end_date: str):
    """Main function to analyze school chats"""
    analyzer = ChatAnalytics(school_queue, start_date, end_date)
    
    # Generate and print statistics
    stats = analyzer.generate_statistics()
    print("\nChat Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Save all visualizations
    analyzer.save_all_visualizations(f"{school_queue}_analysis")
    
    return analyzer.df

if __name__ == "__main__":
    # Example usage
    df = analyze_school_chats(
        school_queue="toronto-st-george",
        start_date="2018-01-01",
        end_date="2020-05-31"
    )