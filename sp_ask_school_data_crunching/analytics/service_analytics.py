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
    find_school_by_queue_or_profile_name
)
from .school_analytics import SchoolChatAnalytics

class ServiceAnalytics:
    """Analyze chat service across all institutions"""
    
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
        self.df = self._fetch_all_data()
        
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
            
        return pd.DataFrame(all_chats)
    
    def analyze_service_overview(self) -> Dict:
        """Generate service-wide statistics"""
        stats = {
            'Total Statistics': {
                'total_chats': len(self.df),
                'unique_operators': self.df['operator'].nunique(),
                'average_duration': self.df['duration'].mean() / 60,  # in minutes
                'average_wait_time': self.df['wait'].mean() / 60,  # in minutes
                'total_chat_time': self.df['duration'].sum() / 3600  # in hours
            }
        }
        
        # Add school-specific stats
        school_stats = {}
        for school in sp_ask_school_dict:
            school_name = school['school']['short_name']
            school_queues = school['school']['queues']
            
            school_chats = self.df[self.df['queue'].isin(school_queues)]
            if len(school_chats) > 0:
                school_stats[school_name] = {
                    'total_chats': len(school_chats),
                    'percentage_of_total': (len(school_chats) / len(self.df)) * 100,
                    'average_duration': school_chats['duration'].mean() / 60,
                    'average_wait_time': school_chats['wait'].mean() / 60
                }
        
        stats['School Statistics'] = school_stats
        return stats
    
    def create_service_visualizations(self):
        """Generate service-wide visualizations"""
        # 1. Overall chat volume by school
        school_volumes = []
        for school in sp_ask_school_dict:
            school_name = school['school']['short_name']
            school_queues = school['school']['queues']
            volume = len(self.df[self.df['queue'].isin(school_queues)])
            school_volumes.append({
                'school': school_name,
                'chats': volume
            })
        
        volume_df = pd.DataFrame(school_volumes)
        fig_volume = px.bar(
            volume_df,
            x='school',
            y='chats',
            title='Chat Volume by Institution',
        )
        fig_volume.write_html("service_volume_analysis.html")
        
        # 2. Cross-institutional collaboration
        def get_operator_school(operator):
            if pd.isna(operator):
                return None
            return find_school_by_operator_suffix(operator)
        
        self.df['operator_school'] = self.df['operator'].apply(get_operator_school)
        self.df['queue_school'] = self.df['queue'].apply(find_school_by_queue_or_profile_name)
        
        collaboration_data = (self.df[['operator_school', 'queue_school']]
                            .value_counts()
                            .reset_index(name='count'))
        
        fig_collab = px.sunburst(
            collaboration_data,
            path=['queue_school', 'operator_school'],
            values='count',
            title='Cross-institutional Chat Support'
        )
        fig_collab.write_html("service_collaboration_analysis.html")
        
        # 3. Service-wide time patterns
        self.df['hour'] = pd.to_datetime(self.df['started']).dt.hour
        self.df['day_of_week'] = pd.to_datetime(self.df['started']).dt.day_name()
        
        fig_time = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Hourly Distribution', 'Daily Distribution')
        )
        
        hourly_counts = self.df['hour'].value_counts().sort_index()
        fig_time.add_trace(
            go.Bar(x=hourly_counts.index, y=hourly_counts.values, name='Hourly'),
            row=1, col=1
        )
        
        daily_counts = self.df['day_of_week'].value_counts()
        fig_time.add_trace(
            go.Bar(x=daily_counts.index, y=daily_counts.values, name='Daily'),
            row=2, col=1
        )
        
        fig_time.update_layout(height=800, title_text='Service-wide Time Patterns')
        fig_time.write_html("service_time_analysis.html")
        
        # 4. Combined dashboard
        self.create_service_dashboard()
    
    def create_service_dashboard(self):
        """Create a comprehensive service dashboard"""
        stats = self.analyze_service_overview()
        
        # Create HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ask a Librarian Service Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: auto;
                }}
                .stats-card {{
                    background: white;
                    padding: 20px;
                    margin: 10px 0;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .school-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                }}
                .visualization {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Ask a Librarian Service Overview</h1>
                <p>Period: {self.start_date} to {self.end_date}</p>
                
                <!-- Overall Statistics -->
                <div class="stats-card">
                    <h2>Service-wide Statistics</h2>
                    <p>Total Chats: {stats['Total Statistics']['total_chats']:,}</p>
                    <p>Unique Operators: {stats['Total Statistics']['unique_operators']}</p>
                    <p>Average Duration: {stats['Total Statistics']['average_duration']:.2f} minutes</p>
                    <p>Average Wait Time: {stats['Total Statistics']['average_wait_time']:.2f} minutes</p>
                    <p>Total Chat Time: {stats['Total Statistics']['total_chat_time']:.2f} hours</p>
                </div>
                
                <!-- School Statistics -->
                <h2>Institution Statistics</h2>
                <div class="school-grid">
                    {self._generate_school_cards(stats['School Statistics'])}
                </div>
                
                <!-- Visualizations -->
                <div id="volumeChart" class="visualization"></div>
                <div id="timeChart" class="visualization"></div>
                <div id="collaborationChart" class="visualization"></div>
            </div>
        </body>
        </html>
        """
        
        with open("service_dashboard.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_school_cards(self, school_stats: Dict) -> str:
        """Generate HTML for school statistics cards"""
        cards_html = ""
        for school, stats in school_stats.items():
            cards_html += f"""
                <div class="stats-card">
                    <h3>{school}</h3>
                    <p>Total Chats: {stats['total_chats']:,}</p>
                    <p>Percentage of Service: {stats['percentage_of_total']:.1f}%</p>
                    <p>Average Duration: {stats['average_duration']:.2f} minutes</p>
                    <p>Average Wait Time: {stats['average_wait_time']:.2f} minutes</p>
                </div>
            """
        return cards_html

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