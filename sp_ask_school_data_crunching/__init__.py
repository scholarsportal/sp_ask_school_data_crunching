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
import numpy as np
from scipy import stats

class EnhancedChatAnalytics:
    def __init__(self, school_queue: str, start_date: str, end_date: str):
        """Initialize ChatAnalytics with school and date range"""
        self.school_queue = school_queue
        self.start_date = start_date
        self.end_date = end_date
        self.df = self._fetch_data()
        self._prepare_data()
        
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch and prepare chat data"""
        # Initialize client
        client = lh3.api.Client()
        
        # Convert strings to datetime objects
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
        
        all_chats = []
        current_date = start_dt
        
        print(f"Fetching data for {self.school_queue}...")
        
        while current_date <= end_dt:
            try:
                daily_chats = client.chats().list_day(
                    current_date.year,
                    current_date.month,
                    current_date.day
                )
                
                if daily_chats:
                    # Filter chats for specific queue
                    queue_chats = [
                        chat for chat in daily_chats 
                        if chat.get('queue') == self.school_queue
                    ]
                    all_chats.extend(queue_chats)
                    print(f"Fetched {len(queue_chats)} chats for {current_date.date()}")
                    
            except Exception as e:
                print(f"Error fetching data for {current_date.date()}: {str(e)}")
                
            # Move to next day
            current_date += timedelta(days=1)
        
        if not all_chats:
            raise ValueError(f"No chats found for {self.school_queue} in the specified date range")
            
        return pd.DataFrame(all_chats)

    def _prepare_data(self):
        """Prepare data by adding derived columns"""
        # Convert timestamp columns to datetime
        for col in ['started', 'accepted', 'ended']:
            self.df[col] = pd.to_datetime(self.df[col])
        
        # Add derived columns
        self.df['hour'] = self.df['started'].dt.hour
        self.df['day_of_week'] = self.df['started'].dt.day_name()
        self.df['month'] = self.df['started'].dt.to_period('M')
        self.df['month_num'] = self.df['started'].dt.month
        self.df['year'] = self.df['started'].dt.year
        self.df['date'] = self.df['started'].dt.date
        
    def create_time_analysis_plots(self) -> go.Figure:
        """Create detailed time analysis visualizations"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Hourly Chat Distribution',
                'Day of Week Distribution',
                'Chat Duration by Hour',
                'Wait Times by Hour'
            )
        )
        
        # Hourly distribution
        hourly_counts = self.df.groupby('hour')['id'].count()
        fig.add_trace(
            go.Bar(x=hourly_counts.index, y=hourly_counts.values, name='Chats per Hour'),
            row=1, col=1
        )
        
        # Daily distribution
        daily_counts = self.df['day_of_week'].value_counts()
        fig.add_trace(
            go.Bar(x=daily_counts.index, y=daily_counts.values, name='Chats per Day'),
            row=1, col=2
        )
        
        # Duration by hour
        hourly_duration = self.df.groupby('hour')['duration'].mean()
        fig.add_trace(
            go.Scatter(x=hourly_duration.index, y=hourly_duration.values, 
                      mode='lines+markers', name='Avg Duration'),
            row=2, col=1
        )
        
        # Wait times by hour
        hourly_wait = self.df.groupby('hour')['wait'].mean()
        fig.add_trace(
            go.Scatter(x=hourly_wait.index, y=hourly_wait.values, 
                      mode='lines+markers', name='Avg Wait Time'),
            row=2, col=2
        )
        
        fig.update_layout(height=800, title_text='Detailed Time Analysis')
        return fig
    
    def create_operator_performance_analysis(self) -> go.Figure:
        """Create detailed operator performance analysis"""
        operator_stats = self.df.groupby('operator').agg({
            'id': 'count',
            'duration': ['mean', 'std'],
            'wait': ['mean', 'std']
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Chats per Operator',
                'Average Duration per Operator',
                'Average Wait Time per Operator',
                'Operator Efficiency Score'
            )
        )
        
        # Calculate efficiency score (lower wait times, optimal duration)
        operator_stats['efficiency_score'] = (
            operator_stats[('duration', 'mean')] / operator_stats[('wait', 'mean')]
        )
        
        # Add traces
        fig.add_trace(
            go.Bar(x=operator_stats['operator'], 
                  y=operator_stats[('id', 'count')],
                  name='Total Chats'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=operator_stats['operator'],
                  y=operator_stats[('duration', 'mean')],
                  name='Avg Duration'),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(x=operator_stats['operator'],
                  y=operator_stats[('wait', 'mean')],
                  name='Avg Wait'),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(x=operator_stats['operator'],
                  y=operator_stats['efficiency_score'],
                  name='Efficiency'),
            row=2, col=2
        )
        
        fig.update_layout(height=1000, 
                         title_text='Operator Performance Analysis',
                         showlegend=True)
        return fig
    
    def create_seasonal_analysis(self) -> go.Figure:
        """Create seasonal analysis visualization"""
        self.df['month_num'] = self.df['started'].dt.month
        self.df['year'] = self.df['started'].dt.year
        
        monthly_trends = self.df.groupby(['year', 'month_num'])['id'].count().reset_index()
        
        fig = go.Figure()
        
        for year in monthly_trends['year'].unique():
            year_data = monthly_trends[monthly_trends['year'] == year]
            fig.add_trace(
                go.Scatter(x=year_data['month_num'],
                          y=year_data['id'],
                          name=str(year),
                          mode='lines+markers')
            )
            
        fig.update_layout(
            title='Seasonal Chat Patterns by Year',
            xaxis_title='Month',
            yaxis_title='Number of Chats',
            xaxis=dict(tickmode='array',
                      ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                      tickvals=list(range(1, 13)))
        )
        return fig
    
    def compare_time_periods(self, period1: Tuple[str, str], 
                           period2: Tuple[str, str]) -> Dict:
        """Compare statistics between two time periods"""
        def get_period_stats(start, end):
            mask = (self.df['started'] >= start) & (self.df['started'] <= end)
            period_df = self.df[mask]
            
            return {
                'total_chats': len(period_df),
                'avg_duration': period_df['duration'].mean(),
                'avg_wait': period_df['wait'].mean(),
                'peak_hour': period_df.groupby('hour')['id'].count().idxmax(),
                'busiest_day': period_df['day_of_week'].mode()[0],
                'unique_operators': period_df['operator'].nunique(),
                'chats_per_day': len(period_df) / period_df['started'].dt.date.nunique()
            }
        
        stats1 = get_period_stats(period1[0], period1[1])
        stats2 = get_period_stats(period2[0], period2[1])
        
        # Calculate percentage changes
        comparison = {}
        for key in stats1.keys():
            if isinstance(stats1[key], (int, float)):
                pct_change = ((stats2[key] - stats1[key]) / stats1[key]) * 100
                comparison[key] = {
                    'period1': stats1[key],
                    'period2': stats2[key],
                    'pct_change': pct_change
                }
            else:
                comparison[key] = {
                    'period1': stats1[key],
                    'period2': stats2[key]
                }
        
        return comparison
    
    def advanced_statistics(self) -> Dict:
        """Generate advanced statistical analysis"""
        stats = {
            'Basic Stats': {
                'total_chats': len(self.df),
                'unique_operators': self.df['operator'].nunique(),
                'avg_duration': self.df['duration'].mean(),
                'median_duration': self.df['duration'].median(),
                'duration_std': self.df['duration'].std()
            },
            'Time Analysis': {
                'peak_hours': self.df.groupby('hour')['id'].count().nlargest(3).to_dict(),
                'busiest_days': self.df['day_of_week'].value_counts().head(3).to_dict(),
                'avg_chats_per_day': len(self.df) / self.df['started'].dt.date.nunique()
            },
            'Operator Analysis': {
                'top_operators': self.df['operator'].value_counts().head(5).to_dict(),
                'avg_chats_per_operator': len(self.df) / self.df['operator'].nunique()
            },
            'Wait Time Analysis': {
                'avg_wait': self.df['wait'].mean(),
                'median_wait': self.df['wait'].median(),
                'wait_90th_percentile': self.df['wait'].quantile(0.9)
            }
        }
        
        # Add correlation analysis
        correlations = {
            'wait_duration_corr': stats.pearsonr(
                self.df['wait'], 
                self.df['duration']
            )[0]
        }
        
        # Add trend analysis
        self.df['date'] = self.df['started'].dt.date
        daily_counts = self.df.groupby('date')['id'].count()
        trend = np.polyfit(range(len(daily_counts)), daily_counts.values, 1)
        
        stats['Trend Analysis'] = {
            'slope': trend[0],  # Positive means increasing trend
            'trend_direction': 'Increasing' if trend[0] > 0 else 'Decreasing',
            'correlation_coefficient': correlations['wait_duration_corr']
        }
        
        return stats

def analyze_school_chats(school_queue: str, start_date: str, end_date: str):
    """Main function to analyze school chats"""
    try:
        analyzer = EnhancedChatAnalytics(school_queue, start_date, end_date)
        
        # Create and save visualizations
        analyzer.create_time_analysis_plots().write_html(f"{school_queue}_time_analysis.html")
        analyzer.create_operator_performance_analysis().write_html(f"{school_queue}_operator_analysis.html")
        analyzer.create_seasonal_analysis().write_html(f"{school_queue}_seasonal_analysis.html")
        
        # Get statistics
        stats = analyzer.advanced_statistics()
        print("\nAdvanced Statistics:")
        for category, values in stats.items():
            print(f"\n{category}:")
            for key, value in values.items():
                print(f"  {key}: {value}")
        
        return analyzer
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return None
    
if __name__ == "__main__":
    # Example usage
    analyzer = EnhancedChatAnalytics(
        school_queue="toronto-st-george",
        start_date="2018-01-01",
        end_date="2020-05-31"
    )
    
    # Generate and save visualizations
    analyzer.create_time_analysis_plots().write_html("time_analysis.html")
    analyzer.create_operator_performance_analysis().write_html("operator_analysis.html")
    analyzer.create_seasonal_analysis().write_html("seasonal_analysis.html")
    
    # Compare two time periods
    comparison = analyzer.compare_time_periods(
        ("2018-01-01", "2018-12-31"),
        ("2019-01-01", "2019-12-31")
    )
    print("\nYear-over-Year Comparison:")
    for metric, values in comparison.items():
        print(f"\n{metric}:")
        for key, value in values.items():
            print(f"  {key}: {value}")
    
    # Get advanced statistics
    stats = analyzer.advanced_statistics()
    print("\nAdvanced Statistics:")
    for category, values in stats.items():
        print(f"\n{category}:")
        for key, value in values.items():
            print(f"  {key}: {value}")