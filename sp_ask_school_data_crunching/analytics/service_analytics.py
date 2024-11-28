from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import lh3.api
from typing import List, Dict, Any, Tuple
import numpy as np
from scipy import stats
from sp_ask_school import (
    sp_ask_school_dict,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
    FRENCH_QUEUES,
    SMS_QUEUES
)

class ServiceAnalytics:
    def __init__(self, start_date: str, end_date: str):
        """
        Initialize service-wide analytics
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        self.start_date = start_date
        self.end_date = end_date
        self.schools_data = {}  # Store individual school analyzers
        print(f"\nInitializing service analysis for period: {start_date} to {end_date}")
        self.df = self._fetch_all_data()
        self._prepare_data()
        
    def _fetch_all_data(self) -> pd.DataFrame:
        """Fetch chat data for all schools"""
        print("Fetching data for all schools...")
        client = lh3.api.Client()
        
        all_chats = []
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
        current_date = start_dt
        
        while current_date <= end_dt:
            try:
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
                
            current_date += timedelta(days=1)
        
        print(f"Total chats fetched: {len(all_chats)}")
        return pd.DataFrame(all_chats)
    
    def _prepare_data(self):
        """Prepare data for analysis"""
        # Convert timestamps
        self.df['started'] = pd.to_datetime(self.df['started'])
        self.df['ended'] = pd.to_datetime(self.df['ended'])
        self.df['accepted'] = pd.to_datetime(self.df['accepted'])
        
        # Add derived columns
        self.df['hour'] = self.df['started'].dt.hour
        self.df['day_of_week'] = self.df['started'].dt.day_name()
        self.df['month'] = self.df['started'].dt.to_period('M')
        self.df['is_abandoned'] = self.df['accepted'].isna()
        
        # Add queue type flags
        self.df['is_french'] = self.df['queue'].isin(FRENCH_QUEUES)
        self.df['is_sms'] = self.df['queue'].isin(SMS_QUEUES)
        
        print("Data preparation complete.")

    def analyze_service_overview(self) -> Dict:
        """Generate comprehensive service-wide statistics"""
        # Basic service stats
        total_duration = self.df['duration'].sum()
        total_wait = self.df['wait'].sum()
        
        stats = {
            'Service Overview': {
                'total_chats': len(self.df),
                'unique_operators': self.df['operator'].nunique(),
                'total_chat_time_hours': total_duration / 3600,
                'total_wait_time_hours': total_wait / 3600,
                'average_duration_minutes': self.df['duration'].mean() / 60,
                'average_wait_minutes': self.df['wait'].mean() / 60,
                'median_duration_minutes': self.df['duration'].median() / 60,
                'median_wait_minutes': self.df['wait'].median() / 60
            },
            'Service Efficiency': {
                'chats_per_day': len(self.df) / self.df['started'].dt.date.nunique(),
                'peak_hour': self.df.groupby(self.df['started'].dt.hour)['id'].count().idxmax(),
                'busiest_day': self.df['started'].dt.day_name().mode()[0],
                'abandoned_rate': (self.df['accepted'].isna().sum() / len(self.df)) * 100
            },
            'Queue Types': {
                'french_chats': len(self.df[self.df['queue'].isin(FRENCH_QUEUES)]),
                'sms_chats': len(self.df[self.df['queue'].isin(SMS_QUEUES)]),
                'french_percentage': (len(self.df[self.df['queue'].isin(FRENCH_QUEUES)]) / len(self.df)) * 100,
                'sms_percentage': (len(self.df[self.df['queue'].isin(SMS_QUEUES)]) / len(self.df)) * 100
            }
        }
        
        # Add monthly trends
        monthly_counts = self.df.groupby(self.df['started'].dt.to_period('M'))['id'].count()
        stats['Monthly Trends'] = {
            'highest_volume_month': str(monthly_counts.idxmax()),
            'lowest_volume_month': str(monthly_counts.idxmin()),
            'monthly_average': monthly_counts.mean(),
            'monthly_std': monthly_counts.std()
        }
        
        return stats

    def create_service_visualizations(self):
        """Generate enhanced service-wide visualizations"""
        
        # 1. Monthly Trends with Queue Types
        monthly_stats = self.df.groupby(self.df['started'].dt.to_period('M')).agg({
            'id': 'count',
            'duration': 'mean',
            'wait': 'mean'
        }).reset_index()
        monthly_stats['started'] = monthly_stats['started'].astype(str)
        
        fig_monthly = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Monthly Chat Volume', 'Average Response Metrics'),
            vertical_spacing=0.15
        )
        
        fig_monthly.add_trace(
            go.Bar(
                x=monthly_stats['started'],
                y=monthly_stats['id'],
                name='Total Chats'
            ),
            row=1, col=1
        )
        
        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_stats['started'],
                y=monthly_stats['duration']/60,
                name='Avg Duration (min)',
                mode='lines+markers'
            ),
            row=2, col=1
        )
        
        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_stats['started'],
                y=monthly_stats['wait']/60,
                name='Avg Wait (min)',
                mode='lines+markers'
            ),
            row=2, col=1
        )
        
        fig_monthly.update_layout(height=800, title_text='Monthly Service Patterns')
        fig_monthly.write_html("service_monthly_analysis.html")
        
        # 2. Operator Performance Distribution
        operator_stats = self.df.groupby('operator').agg({
            'id': 'count',
            'duration': 'mean',
            'wait': 'mean'
        }).reset_index()
        
        fig_operator = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Chats per Operator Distribution',
                'Average Duration Distribution',
                'Response Time Distribution',
                'Operator Load Distribution'
            )
        )
        
        fig_operator.add_trace(
            go.Histogram(x=operator_stats['id'], name='Chats per Operator'),
            row=1, col=1
        )
        
        fig_operator.add_trace(
            go.Histogram(x=operator_stats['duration']/60, name='Avg Duration (min)'),
            row=1, col=2
        )
        
        fig_operator.add_trace(
            go.Histogram(x=operator_stats['wait']/60, name='Avg Wait (min)'),
            row=2, col=1
        )
        
        fig_operator.add_trace(
            go.Box(y=operator_stats['id'], name='Operator Load'),
            row=2, col=2
        )
        
        fig_operator.update_layout(height=1000, title_text='Operator Performance Analysis')
        fig_operator.write_html("service_operator_analysis.html")
            

        # 3. Queue Type Analysis
        queue_stats = self.df.groupby('queue').agg({
            'id': 'count',
            'duration': 'mean',
            'wait': 'mean'
        }).reset_index()
        
        # Identify queue types
        queue_stats['type'] = 'Regular'
        queue_stats.loc[queue_stats['queue'].isin(FRENCH_QUEUES), 'type'] = 'French'
        queue_stats.loc[queue_stats['queue'].isin(SMS_QUEUES), 'type'] = 'SMS'
        
        # Create separate figures for different chart types
        # Pie chart for volume
        volume_by_type = queue_stats.groupby('type')['id'].sum()
        fig_volume = go.Figure(data=[go.Pie(
            labels=volume_by_type.index,
            values=volume_by_type.values,
            title='Chat Volume by Queue Type'
        )])
        
        # Create subplot for the other analyses
        fig_queues = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Average Duration by Queue Type',
                'Average Wait Time by Queue Type',
                'Queue Performance Comparison',
                'Queue Load Distribution'
            )
        )
        
        # Add duration by type
        duration_by_type = queue_stats.groupby('type')['duration'].mean()/60
        fig_queues.add_trace(
            go.Bar(
                x=duration_by_type.index,
                y=duration_by_type.values,
                name='Avg Duration (min)'
            ),
            row=1, col=1
        )
        
        # Add wait time by type
        wait_by_type = queue_stats.groupby('type')['wait'].mean()/60
        fig_queues.add_trace(
            go.Bar(
                x=wait_by_type.index,
                y=wait_by_type.values,
                name='Avg Wait (min)'
            ),
            row=1, col=2
        )
        
        # Add scatter plot of duration vs wait time
        fig_queues.add_trace(
            go.Scatter(
                x=queue_stats['duration']/60,
                y=queue_stats['wait']/60,
                mode='markers',
                name='Queue Performance',
                text=queue_stats['queue'],
                marker=dict(
                    color=queue_stats['id'],
                    showscale=True,
                    colorscale='Viridis',
                    size=queue_stats['id']/10,
                    sizeref=2.*max(queue_stats['id'])/(40.**2),
                    sizemin=4
                )
            ),
            row=2, col=1
        )
        
        # Add box plots for load distribution
        fig_queues.add_trace(
            go.Box(
                y=queue_stats['id'],
                x=queue_stats['type'],
                name='Load Distribution'
            ),
            row=2, col=2
        )
        
        # Update layouts
        fig_volume.update_layout(
            title='Chat Volume Distribution',
            height=600
        )
        
        fig_queues.update_layout(
            height=1000,
            title_text='Queue Performance Analysis',
            showlegend=True
        )
        
        # Add axes labels
        fig_queues.update_xaxes(title_text="Queue Type", row=1, col=1)
        fig_queues.update_xaxes(title_text="Queue Type", row=1, col=2)
        fig_queues.update_xaxes(title_text="Average Duration (minutes)", row=2, col=1)
        fig_queues.update_xaxes(title_text="Queue Type", row=2, col=2)
        
        fig_queues.update_yaxes(title_text="Minutes", row=1, col=1)
        fig_queues.update_yaxes(title_text="Minutes", row=1, col=2)
        fig_queues.update_yaxes(title_text="Average Wait Time (minutes)", row=2, col=1)
        fig_queues.update_yaxes(title_text="Number of Chats", row=2, col=2)
        
        # Save figures
        fig_volume.write_html("service_queue_volume.html")
        fig_queues.write_html("service_queue_performance.html")

def analyze_service(start_date: str, end_date: str):
    """Main function to analyze entire chat service"""
    try:
        analyzer = ServiceAnalytics(start_date, end_date)
        stats = analyzer.analyze_service_overview()
        
        print("\nGenerating service-wide visualizations...")
        analyzer.create_service_visualizations()
        
        print("\nService Analysis Complete!")
        print(f"Generated files:")
        print("1. service_dashboard.html")
        print("2. service_volume_analysis.html")
        print("3. service_collaboration_analysis.html")
        print("4. service_time_analysis.html")
        
        return analyzer, stats
        
    except Exception as e:
        print(f"Error during service analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None