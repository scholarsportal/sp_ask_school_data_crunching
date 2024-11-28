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
    sp_ask_school_dict,
    find_school_by_operator_suffix,
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


    def create_time_analysis(self):
        """Create comprehensive time analysis visualization with four plots"""
        school_name = self.school_info['school']['full_name'].replace(' ', '_')
        
        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Hourly Chat Distribution',
                'Day of Week Distribution',
                'Average Chat Duration by Hour',
                'Average Wait Time by Hour'
            ),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )

        # 1. Hourly distribution
        hourly_counts = self.df.groupby('hour')['id'].count()
        fig.add_trace(
            go.Bar(
                x=hourly_counts.index, 
                y=hourly_counts.values,
                name='Chats per Hour',
                marker_color='rgb(55, 83, 109)',
                hovertemplate="Hour: %{x}:00<br>Number of Chats: %{y}<extra></extra>"
            ),
            row=1, col=1
        )

        # 2. Daily distribution
        daily_counts = self.df['day_of_week'].value_counts()
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_counts = daily_counts.reindex(days_order)
        fig.add_trace(
            go.Bar(
                x=daily_counts.index,
                y=daily_counts.values,
                name='Chats per Day',
                marker_color='rgb(26, 118, 255)',
                hovertemplate="Day: %{x}<br>Number of Chats: %{y}<extra></extra>"
            ),
            row=1, col=2
        )

        # 3. Duration by hour (convert to minutes)
        hourly_duration = self.df.groupby('hour')['duration'].mean() / 60  # Convert to minutes
        fig.add_trace(
            go.Scatter(
                x=hourly_duration.index,
                y=hourly_duration.values,
                mode='lines+markers',
                name='Avg Duration',
                line=dict(color='rgb(219, 64, 82)', width=2),
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Average Duration: %{y:.1f} minutes<extra></extra>"
                )
            ),
            row=2, col=1
        )

        # 4. Wait times by hour (convert to minutes)
        hourly_wait = self.df.groupby('hour')['wait'].mean() / 60  # Convert to minutes
        fig.add_trace(
            go.Scatter(
                x=hourly_wait.index,
                y=hourly_wait.values,
                mode='lines+markers',
                name='Avg Wait Time',
                line=dict(color='rgb(0, 177, 106)', width=2),
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Average Wait Time: %{y:.1f} minutes<extra></extra>"
                )
            ),
            row=2, col=2
        )

        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f'Time Analysis for {self.school_info["school"]["full_name"]}',
        )

        # Update x-axes with hour formatting for time plots
        fig.update_xaxes(
            title_text="Hour of Day", 
            ticktext=['{}:00'.format(str(i).zfill(2)) for i in range(24)],
            tickvals=list(range(24)),
            row=1, col=1
        )
        fig.update_xaxes(title_text="Day of Week", row=1, col=2)
        fig.update_xaxes(
            title_text="Hour of Day",
            ticktext=['{}:00'.format(str(i).zfill(2)) for i in range(24)],
            tickvals=list(range(24)),
            row=2, col=1
        )
        fig.update_xaxes(
            title_text="Hour of Day",
            ticktext=['{}:00'.format(str(i).zfill(2)) for i in range(24)],
            tickvals=list(range(24)),
            row=2, col=2
        )

        # Update y-axes
        fig.update_yaxes(title_text="Number of Chats", row=1, col=1)
        fig.update_yaxes(title_text="Number of Chats", row=1, col=2)
        fig.update_yaxes(title_text="Average Duration (minutes)", row=2, col=1)
        fig.update_yaxes(title_text="Average Wait Time (minutes)", row=2, col=2)

        # Save the figure
        fig.write_html(f"{school_name}_time_analysis.html")
        print(f"Generated time analysis visualization: {school_name}_time_analysis.html")

    def create_advanced_time_analysis(self):
        """Create comprehensive time analysis with additional metrics"""
        school_name = self.school_info['school']['full_name'].replace(' ', '_')
        
        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Hourly Chat Volume',
                'Response Time Distribution by Hour',
                'Chat Duration by Day of Week',
                'Concurrent Chats by Hour',
                'Operator Activity Heatmap',
                'Abandonment Rate by Hour'
            ),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )

        # 1. Hourly Chat Volume (Original plot enhanced)
        hourly_counts = self.df.groupby('hour')['id'].count()
        fig.add_trace(
            go.Bar(
                x=hourly_counts.index, 
                y=hourly_counts.values,
                name='Volume',
                marker_color='rgb(55, 83, 109)',
                hovertemplate="Hour: %{x}:00<br>Chats: %{y}<extra></extra>"
            ),
            row=1, col=1
        )

        # 2. Response Time Distribution
        self.df['response_time'] = (
            pd.to_datetime(self.df['accepted']) - 
            pd.to_datetime(self.df['started'])
        ).dt.total_seconds() / 60  # Convert to minutes
        
        hourly_response = self.df.groupby('hour')['response_time'].agg(['mean', 'std']).fillna(0)
        
        fig.add_trace(
            go.Scatter(
                x=hourly_response.index,
                y=hourly_response['mean'],
                mode='lines+markers',
                name='Avg Response',
                line=dict(color='rgb(26, 118, 255)'),
                error_y=dict(
                    type='data',
                    array=hourly_response['std'],
                    visible=True
                ),
                hovertemplate="Hour: %{x}:00<br>Response Time: %{y:.1f}±%{error_y.array:.1f} min<extra></extra>"
            ),
            row=1, col=2
        )

        # 3. Chat Duration by Day of Week
        daily_duration = self.df.groupby('day_of_week')['duration'].agg(['mean', 'std']).reindex(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        )
        daily_duration['mean'] = daily_duration['mean'] / 60  # Convert to minutes
        daily_duration['std'] = daily_duration['std'] / 60    # Convert to minutes
        
        fig.add_trace(
            go.Bar(
                x=daily_duration.index,
                y=daily_duration['mean'],
                error_y=dict(type='data', array=daily_duration['std']),
                name='Duration',
                marker_color='rgb(219, 64, 82)',
                hovertemplate="Day: %{x}<br>Duration: %{y:.1f}±%{error_y.array:.1f} min<extra></extra>"
            ),
            row=2, col=1
        )

        # 4. Concurrent Chats Analysis
        def count_concurrent(group):
            times = []
            counts = []
            for _, row in group.iterrows():
                start = pd.to_datetime(row['started'])
                end = pd.to_datetime(row['ended'])
                times.extend([start, end])
                counts.extend([1, -1])
            df_times = pd.DataFrame({'time': times, 'count': counts}).sort_values('time')
            return df_times['count'].cumsum().max()

        self.df['hour_date'] = pd.to_datetime(self.df['started']).dt.floor('h')
        concurrent_chats = self.df.groupby('hour')['started'].apply(
            lambda x: count_concurrent(self.df[self.df['hour'] == x.name])
        )
        
        fig.add_trace(
            go.Scatter(
                x=concurrent_chats.index,
                y=concurrent_chats.values,
                mode='lines+markers',
                name='Concurrent',
                line=dict(color='rgb(0, 177, 106)'),
                hovertemplate="Hour: %{x}:00<br>Max Concurrent: %{y}<extra></extra>"
            ),
            row=2, col=2
        )

        # 5. Operator Activity Heatmap
        operator_hourly = pd.crosstab(
            self.df['operator'],
            self.df['hour']
        )
        
        fig.add_trace(
            go.Heatmap(
                z=operator_hourly.values,
                x=operator_hourly.columns,
                y=operator_hourly.index,
                colorscale='Viridis',
                name='Activity',
                hovertemplate="Hour: %{x}:00<br>Operator: %{y}<br>Chats: %{z}<extra></extra>"
            ),
            row=3, col=1
        )

        # 6. Abandonment Rate Analysis
        self.df['abandoned'] = self.df['accepted'].isna()
        hourly_abandonment = (
            self.df.groupby('hour')['abandoned']
            .agg(['sum', 'count'])
            .assign(rate=lambda x: (x['sum'] / x['count']) * 100)
        )
        
        fig.add_trace(
            go.Scatter(
                x=hourly_abandonment.index,
                y=hourly_abandonment['rate'],
                mode='lines+markers',
                name='Abandonment',
                line=dict(color='rgb(255, 127, 14)'),
                hovertemplate="Hour: %{x}:00<br>Abandonment Rate: %{y:.1f}%<extra></extra>"
            ),
            row=3, col=2
        )

        # Update layout and axes
        fig.update_layout(
            height=1200,
            showlegend=True,
            title_text=f'Advanced Time Analysis for {self.school_info["school"]["full_name"]}',
        )

        # Update x-axes
        for row, col in [(1,1), (1,2), (2,2), (3,2)]:
            fig.update_xaxes(
                title_text="Hour of Day",
                ticktext=['{}:00'.format(str(i).zfill(2)) for i in range(24)],
                tickvals=list(range(24)),
                row=row, col=col
            )

        # Update specific axis titles
        fig.update_yaxes(title_text="Number of Chats", row=1, col=1)
        fig.update_yaxes(title_text="Response Time (minutes)", row=1, col=2)
        fig.update_yaxes(title_text="Average Duration (minutes)", row=2, col=1)
        fig.update_yaxes(title_text="Concurrent Chats", row=2, col=2)
        fig.update_yaxes(title_text="Operator", row=3, col=1)
        fig.update_yaxes(title_text="Abandonment Rate (%)", row=3, col=2)

        # Save the figure
        fig.write_html(f"{school_name}_advanced_time_analysis.html")
        print(f"Generated advanced time analysis: {school_name}_advanced_time_analysis.html")

    def analyze_operator_location(self):
        """Analyze local vs non-local operator distribution by hour"""
        school_name = self.school_info['school']['full_name'].replace(' ', '_')
        
        # Add operator location analysis to dataframe
        def is_local_operator(row):
            if pd.isna(row['operator']):
                return None
            operator_school = find_school_by_operator_suffix(row['operator'])
            return operator_school.lower() == self.school_info['school']['short_name'].lower()
        
        # Add local operator flag
        self.df['is_local'] = self.df.apply(is_local_operator, axis=1)
        
        # Group by hour and operator type
        hourly_stats = (self.df[self.df['operator'].notna()]
                    .groupby(['hour', 'is_local'])
                    .size()
                    .unstack(fill_value=0))
        
        # Rename columns for clarity
        hourly_stats.columns = ['Non-Local Operators', 'Local Operators']
        
        # Calculate percentages
        hourly_percentages = hourly_stats.div(hourly_stats.sum(axis=1), axis=0) * 100
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Absolute Numbers of Chats by Operator Location',
                'Percentage Distribution of Operator Location'
            ),
            vertical_spacing=0.15
        )
        
        # Add absolute numbers
        fig.add_trace(
            go.Bar(
                name='Local Operators',
                x=hourly_stats.index,
                y=hourly_stats['Local Operators'],
                marker_color='rgb(55, 83, 109)',
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Local Operator Chats: %{y}<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                name='Non-Local Operators',
                x=hourly_stats.index,
                y=hourly_stats['Non-Local Operators'],
                marker_color='rgb(26, 118, 255)',
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Non-Local Operator Chats: %{y}<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )
        
        # Add percentages
        fig.add_trace(
            go.Bar(
                name='Local Operators %',
                x=hourly_percentages.index,
                y=hourly_percentages['Local Operators'],
                marker_color='rgb(55, 83, 109)',
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Local Operator: %{y:.1f}%<br>" +
                    "<extra></extra>"
                )
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                name='Non-Local Operators %',
                x=hourly_percentages.index,
                y=hourly_percentages['Non-Local Operators'],
                marker_color='rgb(26, 118, 255)',
                hovertemplate=(
                    "Hour: %{x}:00<br>" +
                    "Non-Local Operator: %{y:.1f}%<br>" +
                    "<extra></extra>"
                )
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            barmode='stack',
            height=800,
            title_text=f'Local vs Non-Local Operator Analysis for {self.school_info["school"]["full_name"]}',
            showlegend=True
        )
        
        # Update axes
        for row in [1, 2]:
            fig.update_xaxes(
                title_text="Hour of Day",
                ticktext=['{}:00'.format(str(i).zfill(2)) for i in range(24)],
                tickvals=list(range(24)),
                row=row, col=1
            )
        
        fig.update_yaxes(title_text="Number of Chats", row=1, col=1)
        fig.update_yaxes(title_text="Percentage of Chats", row=2, col=1)
        
        # Save the visualization
        fig.write_html(f"{school_name}_operator_location_analysis.html")
        print(f"Generated operator location analysis: {school_name}_operator_location_analysis.html")
        
        # Print summary statistics
        total_chats = len(self.df[self.df['operator'].notna()])
        local_chats = self.df['is_local'].sum()
        local_percentage = (local_chats / total_chats) * 100
        
        print("\nOperator Location Summary:")
        print(f"Total answered chats: {total_chats}")
        print(f"Chats answered by local operators: {local_chats} ({local_percentage:.1f}%)")
        print(f"Chats answered by non-local operators: {total_chats - local_chats} ({100 - local_percentage:.1f}%)")
        
        return hourly_stats, hourly_percentages


    def generate_chord_diagram(self):
        """Generate chord diagram showing chat flow between schools"""
        try:
            school_name = self.school_info['school']['full_name'].replace(' ', '_')
            
            # Create flow data
            flow_data = []
            skipped_chats = 0
            error_details = {
                'no_operator': 0,
                'unknown_operator_school': 0,
                'unknown_queue_school': 0,
                'other_errors': 0
            }
            
            print("Analyzing chat flows...")
            
            # Process each chat
            for index, chat in self.df.iterrows():
                try:
                    # Skip if no operator
                    if pd.isna(chat['operator']) or not chat['operator']:
                        error_details['no_operator'] += 1
                        skipped_chats += 1
                        continue
                    
                    # Get operator's school
                    operator_school = find_school_by_operator_suffix(chat['operator'])
                    if not operator_school:
                        error_details['unknown_operator_school'] += 1
                        skipped_chats += 1
                        continue
                    
                    # Get queue's school
                    queue_school = find_school_by_queue_or_profile_name(chat['queue'])
                    if not queue_school:
                        error_details['unknown_queue_school'] += 1
                        skipped_chats += 1
                        continue
                    
                    # Skip "Unknown" schools
                    if operator_school == "Unknown" or queue_school == "Unknown":
                        error_details['unknown_queue_school'] += 1
                        skipped_chats += 1
                        continue
                    
                    # Add to flow data
                    flow_data.append({
                        "from": str(queue_school),
                        "to": str(operator_school),
                        "value": 1
                    })
                    
                except Exception as e:
                    error_details['other_errors'] += 1
                    skipped_chats += 1
                    continue
            
            # Check if we have any valid data
            if not flow_data:
                print("\nNo valid chat flow data found!")
                print("\nError Details:")
                for error_type, count in error_details.items():
                    print(f"{error_type}: {count}")
                return None
            
            # Print processing summary
            print(f"\nProcessing Summary:")
            print(f"Total processed: {len(flow_data)} chats")
            print(f"Total skipped: {skipped_chats} chats")
            print("\nSkipped Chat Details:")
            for error_type, count in error_details.items():
                print(f"{error_type}: {count}")
            
            # Aggregate the flow data
            flow_df = pd.DataFrame(flow_data)
            flow_counts = (flow_df.groupby(['from', 'to'])
                        .size()
                        .reset_index(name='value'))
            
            # Convert to list of dicts
            flow_list = flow_counts.to_dict('records')
            
            print(f"\nGenerated {len(flow_list)} flow connections")
            
            # Generate HTML file
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Chat Flow Diagram - {self.school_info['school']['full_name']}</title>
                <script src="https://cdn.amcharts.com/lib/4/core.js"></script>
                <script src="https://cdn.amcharts.com/lib/4/charts.js"></script>
                <script src="https://cdn.amcharts.com/lib/4/themes/dark.js"></script>
                <script src="https://cdn.amcharts.com/lib/4/themes/animated.js"></script>
                <style>
                    body {{ 
                        background-color: #30303d;
                        color: white;
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                    }}
                    #chartdiv {{
                        width: 100%;
                        height: 800px;
                    }}
                    .stats {{
                        margin-bottom: 20px;
                        padding: 15px;
                        background-color: rgba(255, 255, 255, 0.1);
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
                <div class="stats">
                    <h2>Chat Flow Analysis</h2>
                    <p>Period: {self.start_date} to {self.end_date}</p>
                    <p>Total valid flows analyzed: {len(flow_data)}</p>
                    <p>Skipped chats: {skipped_chats}</p>
                </div>
                <div id="chartdiv"></div>
                <script>
                am4core.ready(function() {{
                    // Themes
                    am4core.useTheme(am4themes_dark);
                    am4core.useTheme(am4themes_animated);

                    // Create chart
                    var chart = am4core.create("chartdiv", am4charts.ChordDiagram);

                    // Colors
                    chart.colors.saturation = 1;
                    chart.colors.step = 9;

                    // Data
                    chart.data = {flow_list};

                    // Configure
                    chart.dataFields.fromName = "from";
                    chart.dataFields.toName = "to";
                    chart.dataFields.value = "value";

                    chart.nodePadding = 0.5;
                    chart.minNodeSize = 0.01;
                    chart.startAngle = 80;
                    chart.endAngle = chart.startAngle + 360;
                    chart.sortBy = "value";
                    chart.fontSize = 10;

                    // Node template
                    var nodeTemplate = chart.nodes.template;
                    nodeTemplate.readerTitle = "Click to show/hide or drag to rearrange";
                    nodeTemplate.showSystemTooltip = true;
                    nodeTemplate.tooltipText = "{{name}}'s chats: {{total}}";

                    // Label template
                    var label = nodeTemplate.label;
                    label.relativeRotation = 90;
                    label.fillOpacity = 0.4;

                    // Hover state
                    var labelHS = label.states.create("hover");
                    labelHS.properties.fillOpacity = 1;

                    // Link template
                    var linkTemplate = chart.links.template;
                    linkTemplate.strokeOpacity = 0;
                    linkTemplate.fillOpacity = 0.15;
                    linkTemplate.tooltipText = "Chats from {{fromName}} picked up by {{toName}}: {{value.value}}";

                    var hoverState = linkTemplate.states.create("hover");
                    hoverState.properties.fillOpacity = 0.7;
                    hoverState.properties.strokeOpacity = 0.7;

                }}); // end am4core.ready()
                </script>
            </body>
            </html>
            """
            
            # Save the HTML file
            output_file = f"{school_name}_chord_diagram.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Generated chord diagram: {output_file}")
            
            return flow_list
            
        except Exception as e:
            print(f"Error in generate_chord_diagram: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
def analyze_school(school_name: str, start_date: str, end_date: str, generate_report: bool = True):
    """Analyze chat data for a specific school with detailed error handling"""
    analyzer = None
    try:
        print("\nInitializing analysis...")
        analyzer = SchoolChatAnalytics(school_name, start_date, end_date)
        
        print(f"\nAnalysis for {analyzer.school_info['school']['full_name']}")
        print("=" * 50)
        
        # List of analysis tasks to perform
        analysis_tasks = [
            ("Generate HTML report", lambda: analyzer.generate_html_report() if generate_report else None),
            ("Generate visualizations", analyzer.save_individual_visualizations),
            ("Generate time analysis", analyzer.create_time_analysis),
            ("Generate advanced time analysis", analyzer.create_advanced_time_analysis),
            ("Generate chord diagram", analyzer.generate_chord_diagram)
        ]
        
        # Execute each analysis task with error handling
        for task_name, task_func in analysis_tasks:
            print(f"\nExecuting: {task_name}")
            try:
                task_func()
            except Exception as e:
                print(f"Error in {task_name}:")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                import traceback
                print("\nTraceback:")
                traceback.print_exc()
                print("\nContinuing with remaining analyses...\n")
        
        return analyzer
        
    except Exception as e:
        print("\nCritical error during analysis:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nTraceback:")
        traceback.print_exc()
        return analyzer  # Return analyzer even if incomplete, might be useful for debugging

if __name__ == "__main__":
    # Example usage
    analyzer = analyze_school(
        school_name="University of Toronto",
        start_date="2018-01-01",
        end_date="2020-05-31"
    )