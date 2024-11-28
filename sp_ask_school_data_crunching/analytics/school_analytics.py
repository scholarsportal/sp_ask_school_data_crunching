"""School-based chat analytics module."""

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
    find_queues_from_a_school_name,
    get_shortname_by_full_school_name,
    find_school_by_queue_or_profile_name,
    sp_ask_school_dict
)


class SchoolChatAnalytics:
    def __init__(self, school_name: str, start_date: str, end_date: str):
        """
        Initialize Analytics for a school
        
        Args:
            school_name: School name (can be full name or short name)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        self.school_name = school_name
        self.start_date = start_date
        self.end_date = end_date
        
        # Try to find the school in the dictionary
        self.school_info = self._find_school(school_name)
        if not self.school_info:
            raise ValueError(f"School '{school_name}' not found")
            
        self.school_queues = self.school_info['school']['queues']
        self.school_short_name = self.school_info['school']['short_name']
        
        print(f"Analyzing data for {self.school_info['school']['full_name']}")
        print(f"Including queues: {', '.join(self.school_queues)}")
        
        self.df = self._fetch_data()
        self._prepare_data()
        
    def _find_school(self, school_name: str) -> Dict:
        """Find school info by name or short name"""
        # Convert input to lowercase for case-insensitive comparison
        school_name_lower = school_name.lower()
        
        for school in sp_ask_school_dict:
            if (school_name_lower == school['school']['full_name'].lower() or
                school_name_lower == school['school']['short_name'].lower()):
                return school
        return None
        
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch chat data for all school queues"""
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
                    # Filter chats for any of the school's queues
                    school_chats = [
                        chat for chat in daily_chats 
                        if chat.get('queue') in self.school_queues
                    ]
                    all_chats.extend(school_chats)
                    print(f"Fetched {len(school_chats)} chats for {current_date.date()}")
                    
            except Exception as e:
                print(f"Error fetching data for {current_date.date()}: {str(e)}")
                
            current_date += timedelta(days=1)
        
        if not all_chats:
            raise ValueError(f"No chats found for {self.school_name} in the specified date range")
            
        return pd.DataFrame(all_chats)

    def _prepare_data(self):
        """Prepare data with additional columns"""
        # Convert timestamp columns
        for col in ['started', 'accepted', 'ended']:
            self.df[col] = pd.to_datetime(self.df[col])
        
        # Add derived columns
        self.df['hour'] = self.df['started'].dt.hour
        self.df['day_of_week'] = self.df['started'].dt.day_name()
        self.df['month'] = self.df['started'].dt.to_period('M')
        self.df['month_num'] = self.df['started'].dt.month
        self.df['year'] = self.df['started'].dt.year
        self.df['date'] = self.df['started'].dt.date
        
        # Add queue type flags
        self.df['is_french'] = self.df['queue'].str.contains('-fr$', regex=True)
        self.df['is_sms'] = self.df['queue'].str.contains('-txt$', regex=True)
        self.df['is_proactive'] = self.df['queue'].str.contains('proactive', case=False)

    def queue_specific_analysis(self) -> Dict:
        """Analyze chat distribution across different queues"""
        queue_stats = {
            'Queue Distribution': self.df['queue'].value_counts().to_dict(),
            'French Queue Usage': {
                'total_chats': self.df['is_french'].sum(),
                'percentage': (self.df['is_french'].sum() / len(self.df)) * 100
            },
            'SMS Queue Usage': {
                'total_chats': self.df['is_sms'].sum(),
                'percentage': (self.df['is_sms'].sum() / len(self.df)) * 100
            },
            'Proactive Queue Usage': {
                'total_chats': self.df['is_proactive'].sum(),
                'percentage': (self.df['is_proactive'].sum() / len(self.df)) * 100
            }
        }
        
        # Add average metrics per queue
        queue_metrics = self.df.groupby('queue').agg({
            'duration': 'mean',
            'wait': 'mean',
            'id': 'count'
        }).to_dict()
        
        queue_stats['Queue Metrics'] = queue_metrics
        
        return queue_stats

    def advanced_statistics(self) -> Dict:
        """Generate comprehensive statistics"""
        try:
            # Check if we have enough data for correlation
            if len(self.df) > 1 and self.df['wait'].notna().any() and self.df['duration'].notna().any():
                correlation_coefficient, p_value = stats.pearsonr(
                    self.df['wait'].fillna(0), 
                    self.df['duration'].fillna(0)
                )
            else:
                correlation_coefficient = p_value = None

            stats_dict = {
                'Basic Stats': {
                    'total_chats': len(self.df),
                    'unique_operators': self.df['operator'].nunique(),
                    'avg_duration': float(self.df['duration'].mean()),  # Convert to float
                    'median_duration': float(self.df['duration'].median()),  # Convert to float
                    'duration_std': float(self.df['duration'].std())  # Convert to float
                },
                'Time Analysis': {
                    'peak_hours': self.df.groupby('hour')['id'].count().nlargest(3).to_dict(),
                    'busiest_days': self.df['day_of_week'].value_counts().head(3).to_dict(),
                    'avg_chats_per_day': float(len(self.df) / self.df['started'].dt.date.nunique())  # Convert to float
                },
                'Queue Analysis': self.queue_specific_analysis(),
                'Operator Analysis': {
                    'top_operators': self.df['operator'].value_counts().head(5).to_dict(),
                    'avg_chats_per_operator': float(len(self.df) / self.df['operator'].nunique())  # Convert to float
                },
                'Wait Time Analysis': {
                    'avg_wait': float(self.df['wait'].mean()),  # Convert to float
                    'median_wait': float(self.df['wait'].median()),  # Convert to float
                    'wait_90th_percentile': float(self.df['wait'].quantile(0.9))  # Convert to float
                }
            }
            
            stats_dict['Correlation Analysis'] = {
                'wait_duration_correlation': float(correlation_coefficient) if correlation_coefficient is not None else None,
                'correlation_p_value': float(p_value) if p_value is not None else None
            }
            
            return stats_dict
        except Exception as e:
            print(f"Error in advanced_statistics: {str(e)}")
            return {}

    def create_visualizations(self) -> Dict[str, go.Figure]:
        """Create all visualizations for the school"""
        figs = {}
        
        try:
            # 1. Monthly Chat Volume
            monthly_counts = (self.df.groupby(self.df['started'].dt.to_period('M'))
                            .size()
                            .reset_index())
            monthly_counts.columns = ['Month', 'Number of Chats']
            # Convert Period to string for JSON serialization
            monthly_counts['Month'] = monthly_counts['Month'].astype(str)
            
            fig = px.bar(
                monthly_counts,
                x='Month',
                y='Number of Chats',
                title=f'Monthly Chat Volume - {self.school_info["school"]["full_name"]}'
            )
            figs['monthly_volume'] = fig

            # ... [rest of the visualization code remains the same] ...

        except Exception as e:
            print(f"Error creating visualizations: {str(e)}")
            return {}
        
        return figs

    def generate_html_report(self, output_file: str = None):
        """Generate a comprehensive HTML report with all analytics"""
        if output_file is None:
            output_file = f"{self.school_short_name}_analysis_{self.start_date}_to_{self.end_date}.html"

        try:
            # Get statistics and visualizations
            stats = self.advanced_statistics()
            figs = self.create_visualizations()

            # Create HTML content with error handling
            html_content = f"""
            <html>
            <head>
                <title>Chat Analysis Report - {self.school_info['school']['full_name']}</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 1200px; margin: auto; }}
                    .stat-section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    .visualization {{ margin: 30px 0; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f5f5f5; }}
                    .error {{ color: red; padding: 10px; margin: 10px 0; border: 1px solid red; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Chat Analysis Report</h1>
                    <h2>{self.school_info['school']['full_name']}</h2>
                    <p>Period: {self.start_date} to {self.end_date}</p>
            """

            # Add statistics sections
            for category, values in stats.items():
                html_content += f"""
                    <div class="stat-section">
                        <h3>{category}</h3>
                        <table>
                            <tr><th>Metric</th><th>Value</th></tr>
                """
                if isinstance(values, dict):
                    for key, value in values.items():
                        # Handle None values and format numbers
                        if value is None:
                            formatted_value = "N/A"
                        elif isinstance(value, float):
                            formatted_value = f"{value:.2f}"
                        else:
                            formatted_value = str(value)
                        html_content += f"<tr><td>{key}</td><td>{formatted_value}</td></tr>"
                else:
                    html_content += f"<tr><td>{category}</td><td>{values}</td></tr>"
                html_content += "</table></div>"

            # Add visualizations
            for name, fig in figs.items():
                html_content += f"""
                    <div class="visualization">
                        <div id="{name}"></div>
                        <script>
                            try {{
                                var plotlyData = {fig.to_json()};
                                Plotly.newPlot('{name}', plotlyData.data, plotlyData.layout);
                            }} catch (e) {{
                                document.getElementById('{name}').innerHTML = 
                                    '<div class="error">Error loading visualization: ' + e.message + '</div>';
                            }}
                        </script>
                    </div>
                """

            html_content += """
                </div>
            </body>
            </html>
            """

            # Save the report
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"Report generated: {output_file}")

        except Exception as e:
            print(f"Error generating report: {str(e)}")
            # Create a minimal error report
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"""
                <html>
                    <body>
                        <h1>Error Generating Report</h1>
                        <p>An error occurred: {str(e)}</p>
                    </body>
                </html>
                """)


    def save_individual_visualizations(self):
        """Save individual visualizations as separate HTML files"""
        school_name = self.school_info['school']['full_name'].replace(' ', '_')
        base_filename = f"{school_name}_{self.start_date}_to_{self.end_date}"
        
        # 1. Monthly Histogram
        monthly_counts = (self.df.groupby(self.df['started'].dt.to_period('M'))
                        .size()
                        .reset_index())
        monthly_counts.columns = ['Month', 'Number of Chats']
        monthly_counts['Month'] = monthly_counts['Month'].astype(str)
        
        fig = px.bar(
            monthly_counts,
            x='Month',
            y='Number of Chats',
            title=f'Monthly Chat Distribution for {self.school_info["school"]["full_name"]}'
        )
        fig.update_layout(xaxis_tickangle=-45)
        fig.write_html(f"{school_name}_monthly_distribution.html")

        # 2. Daily Heatmap
        hourly_by_day = pd.crosstab(self.df['day_of_week'], self.df['hour'])
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hourly_by_day = hourly_by_day.reindex(days_order)
        
        fig = px.imshow(
            hourly_by_day,
            title=f'Chat Activity Heatmap for {self.school_info["school"]["full_name"]}',
            labels=dict(x='Hour of Day', y='Day of Week', color='Number of Chats'),
            aspect='auto'
        )
        fig.write_html(f"{school_name}_heatmap.html")

        # 3. Operator Analysis
        operator_stats = self.df.groupby('operator').agg({
            'id': 'count',
            'duration': 'mean',
            'wait': 'mean'
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Total Chats by Operator',
                'Average Duration by Operator (seconds)'
            )
        )
        
        fig.add_trace(
            go.Bar(
                x=operator_stats['operator'],
                y=operator_stats['id'],
                name='Total Chats'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=operator_stats['operator'],
                y=operator_stats['duration'],
                name='Average Duration'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=800,
            title_text=f'Operator Performance Analysis for {self.school_info["school"]["full_name"]}',
            showlegend=True
        )
        fig.write_html(f"{school_name}_operator_analysis.html")

        # 4. Seasonal Analysis
        self.df['month_num'] = self.df['started'].dt.month
        self.df['year'] = self.df['started'].dt.year
        
        monthly_trends = self.df.groupby(['year', 'month_num'])['id'].count().reset_index()
        
        fig = go.Figure()
        
        for year in monthly_trends['year'].unique():
            year_data = monthly_trends[monthly_trends['year'] == year]
            fig.add_trace(
                go.Scatter(
                    x=year_data['month_num'],
                    y=year_data['id'],
                    name=str(year),
                    mode='lines+markers'
                )
            )
        
        fig.update_layout(
            title=f'Seasonal Chat Patterns by Year for {self.school_info["school"]["full_name"]}',
            xaxis_title='Month',
            yaxis_title='Number of Chats',
            xaxis=dict(
                tickmode='array',
                ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                tickvals=list(range(1, 13))
            )
        )
        fig.write_html(f"{school_name}_seasonal_analysis.html")

        # 5. Create Dashboard
        dashboard = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Monthly Distribution',
                'Daily Heatmap',
                'Operator Performance'
            ),
            vertical_spacing=0.1,
            specs=[[{"type": "bar"}],
                [{"type": "heatmap"}],
                [{"type": "bar"}]]
        )
        
        # Add all plots to dashboard
        dashboard.add_trace(fig.data[0], row=1, col=1)  # Monthly distribution
        dashboard.add_trace(go.Heatmap(
            z=hourly_by_day.values,
            x=hourly_by_day.columns,
            y=hourly_by_day.index,
            colorscale='Blues'
        ), row=2, col=1)
        dashboard.add_trace(go.Bar(
            x=operator_stats['operator'],
            y=operator_stats['id']
        ), row=3, col=1)
        
        dashboard.update_layout(
            height=1500,
            title_text=f'Chat Analysis Dashboard for {self.school_info["school"]["full_name"]}'
        )
        dashboard.write_html(f"{school_name}_dashboard.html")

        print(f"Generated visualization files for {self.school_info['school']['full_name']}:")
        print(f"1. {school_name}_monthly_distribution.html")
        print(f"2. {school_name}_heatmap.html")
        print(f"3. {school_name}_operator_analysis.html")
        print(f"4. {school_name}_seasonal_analysis.html")
        print(f"5. {school_name}_dashboard.html")


def analyze_school(school_name: str, start_date: str, end_date: str, generate_report: bool = True):
    """Analyze chat data for a specific school"""
    try:
        analyzer = SchoolChatAnalytics(school_name, start_date, end_date)
        
        # Get statistics
        stats = analyzer.advanced_statistics()
        print(f"\nAnalysis for {analyzer.school_info['school']['full_name']}")
        print("=" * 50)
        
        for category, values in stats.items():
            print(f"\n{category}:")
            if isinstance(values, dict):
                for key, value in values.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {values}")

        # Generate comprehensive report
        if generate_report:
            analyzer.generate_html_report()
            
        # Generate individual visualization files
        analyzer.save_individual_visualizations()
        
        return analyzer
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return None
    

if __name__ == "__main__":
    # Example usage
    analyzer = analyze_school(
        school_name="University of Toronto",
        start_date="2018-01-01",
        end_date="2020-05-31"
    )