from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import lh3.api
from typing import Dict, List
from sp_ask_school import sp_ask_school_dict

class ChatTrendAnalysis:
    def __init__(self, base_year: str, comparison_year: str):
        """
        Initialize trend analysis
        
        Args:
            base_year: Base year for comparison (e.g., "2023")
            comparison_year: Year to compare against (e.g., "2024")
        """
        self.base_year = base_year
        self.comparison_year = comparison_year
        self.df = self._fetch_data()
        
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch data for both years"""
        client = lh3.api.Client()
        
        all_chats = []
        # Fetch base year
        start_date = f"{self.base_year}-01-01"
        end_date = f"{self.base_year}-12-31"
        
        print(f"Fetching data for {self.base_year}...")
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_dt:
            try:
                daily_chats = client.chats().list_day(
                    current_date.year,
                    current_date.month,
                    current_date.day
                )
                if daily_chats:
                    all_chats.extend(daily_chats)
                current_date = current_date + pd.Timedelta(days=1)
            except Exception as e:
                print(f"Error fetching {current_date.date()}: {str(e)}")
        
        # Fetch comparison year
        print(f"\nFetching data for {self.comparison_year}...")
        start_date = f"{self.comparison_year}-01-01"
        end_date = f"{self.comparison_year}-12-31"
        
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_dt:
            try:
                daily_chats = client.chats().list_day(
                    current_date.year,
                    current_date.month,
                    current_date.day
                )
                if daily_chats:
                    all_chats.extend(daily_chats)
                current_date = current_date + pd.Timedelta(days=1)
            except Exception as e:
                print(f"Error fetching {current_date.date()}: {str(e)}")
        
        df = pd.DataFrame(all_chats)
        df['started'] = pd.to_datetime(df['started'])
        return df

    def analyze_trends(self) -> Dict:
        """Analyze year-over-year trends by school"""
        trends = {}
        
        # Process each school
        for school in sp_ask_school_dict:
            school_name = school['school']['short_name']
            school_queues = school['school']['queues']
            
            if not school_queues:  # Skip schools with no queues
                continue
            
            # Filter chats for this school
            school_chats = self.df[self.df['queue'].isin(school_queues)].copy()
            if len(school_chats) == 0:
                continue
                
            # Add month and year columns
            school_chats['year'] = school_chats['started'].dt.year
            school_chats['month'] = school_chats['started'].dt.month
            
            # Calculate monthly volumes
            monthly_volumes = (school_chats
                             .groupby(['year', 'month'])
                             .size()
                             .reset_index(name='chats'))
            
            # Create year-specific dataframes
            base_year_data = monthly_volumes[monthly_volumes['year'] == int(self.base_year)]
            comp_year_data = monthly_volumes[monthly_volumes['year'] == int(self.comparison_year)]
            
            # Calculate year-over-year changes
            changes = []
            for month in range(1, 13):
                base_vol = base_year_data[base_year_data['month'] == month]['chats'].values
                comp_vol = comp_year_data[comp_year_data['month'] == month]['chats'].values
                
                if len(base_vol) > 0 and len(comp_vol) > 0:
                    base_value = base_vol[0]
                    comp_value = comp_vol[0]
                    pct_change = ((comp_value - base_value) / base_value) * 100
                    
                    changes.append({
                        'month': month,
                        'base_volume': base_value,
                        'comparison_volume': comp_value,
                        'percent_change': pct_change
                    })
            
            if changes:  # Only include schools with data
                trends[school_name] = {
                    'changes': changes,
                    'average_change': sum(c['percent_change'] for c in changes) / len(changes),
                    'total_base_year': sum(c['base_volume'] for c in changes),
                    'total_comparison_year': sum(c['comparison_volume'] for c in changes),
                    'overall_change': ((sum(c['comparison_volume'] for c in changes) - 
                                      sum(c['base_volume'] for c in changes)) / 
                                     sum(c['base_volume'] for c in changes)) * 100
                }
        
        return trends

    def generate_report(self):
        """Generate trend analysis report"""
        trends = self.analyze_trends()
        
        # Create visualizations
        # 1. Overall changes by school
        overall_changes = {
            'school': [],
            'percent_change': [],
            'direction': []
        }
        
        for school, data in trends.items():
            overall_changes['school'].append(school)
            overall_changes['percent_change'].append(data['overall_change'])
            overall_changes['direction'].append('Increase' if data['overall_change'] > 0 else 'Decrease')
        
        df_changes = pd.DataFrame(overall_changes)
        df_changes = df_changes.sort_values('percent_change')
        
        fig_overall = px.bar(
            df_changes,
            x='school',
            y='percent_change',
            color='direction',
            title=f'Overall Chat Volume Changes ({self.base_year} vs {self.comparison_year})',
            labels={'percent_change': 'Percent Change', 'school': 'School'},
            color_discrete_map={'Increase': 'green', 'Decrease': 'red'}
        )
        
        # 2. Monthly trends for each school
        fig_monthly = go.Figure()
        
        for school, data in trends.items():
            months = [change['month'] for change in data['changes']]
            changes = [change['percent_change'] for change in data['changes']]
            
            fig_monthly.add_trace(
                go.Scatter(
                    x=months,
                    y=changes,
                    name=school,
                    mode='lines+markers'
                )
            )
        
        fig_monthly.update_layout(
            title=f'Monthly Chat Volume Changes by School ({self.base_year} vs {self.comparison_year})',
            xaxis_title='Month',
            yaxis_title='Percent Change',
            xaxis=dict(
                tickmode='array',
                ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                tickvals=list(range(1, 13))
            )
        )
        
        # Generate HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chat Volume Trend Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    max-width: 1200px;
                    margin: auto;
                }}
                .stats {{
                    margin: 20px 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                }}
                .visualization {{
                    margin: 30px 0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                }}
                .decrease {{
                    color: red;
                }}
                .increase {{
                    color: green;
                }}
            </style>
        </head>
        <body>
            <h1>Chat Volume Trend Analysis</h1>
            <h2>{self.base_year} vs {self.comparison_year}</h2>
            
            <div class="stats">
                <h3>Summary</h3>
                <table>
                    <tr>
                        <th>School</th>
                        <th>{self.base_year} Total</th>
                        <th>{self.comparison_year} Total</th>
                        <th>Overall Change</th>
                        <th>Average Monthly Change</th>
                    </tr>
                    {self._generate_table_rows(trends)}
                </table>
            </div>
            
            <div id="overallChart" class="visualization"></div>
            <div id="monthlyChart" class="visualization"></div>
            
            <script>
                {fig_overall.to_json()}
                Plotly.newPlot('overallChart', figOverall.data, figOverall.layout);
                
                {fig_monthly.to_json()}
                Plotly.newPlot('monthlyChart', figMonthly.data, figMonthly.layout);
            </script>
        </body>
        </html>
        """
        
        # Save report
        filename = f"chat_trends_{self.base_year}_vs_{self.comparison_year}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"\nReport generated: {filename}")
        return trends

    def _generate_table_rows(self, trends: Dict) -> str:
        """Generate HTML table rows for trend data"""
        rows = ""
        for school, data in sorted(trends.items(), 
                                 key=lambda x: x[1]['overall_change']):
            change_class = 'increase' if data['overall_change'] > 0 else 'decrease'
            rows += f"""
                <tr>
                    <td>{school}</td>
                    <td>{data['total_base_year']:,}</td>
                    <td>{data['total_comparison_year']:,}</td>
                    <td class="{change_class}">{data['overall_change']:.1f}%</td>
                    <td class="{change_class}">{data['average_change']:.1f}%</td>
                </tr>
            """
        return rows

def analyze_chat_trends(base_year: str, comparison_year: str):
    """Main function to analyze chat trends"""
    analyzer = ChatTrendAnalysis(base_year, comparison_year)
    return analyzer.generate_report()



from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import lh3.api
from typing import Dict, List, Tuple
from sp_ask_school import sp_ask_school_dict

class DateRangeTrendAnalysis:
    def __init__(self, start_date: str, end_date: str):
        """
        Initialize trend analysis with date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        self.current_start = pd.to_datetime(start_date)
        self.current_end = pd.to_datetime(end_date)
        
        # Calculate previous year's date range
        self.prev_start = self.current_start - pd.DateOffset(years=1)
        self.prev_end = self.current_end - pd.DateOffset(years=1)
        
        print(f"Analyzing trends:")
        print(f"Current period: {self.current_start.date()} to {self.current_end.date()}")
        print(f"Previous period: {self.prev_start.date()} to {self.prev_end.date()}")
        
        self.df = self._fetch_data()
    
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch data for both periods"""
        client = lh3.api.Client()
        all_chats = []
        
        # Function to fetch data for a date range
        def fetch_range(start_date: datetime, end_date: datetime, period_name: str):
            current_date = start_date
            print(f"\nFetching {period_name} period...")
            
            while current_date <= end_date:
                try:
                    daily_chats = client.chats().list_day(
                        current_date.year,
                        current_date.month,
                        current_date.day
                    )
                    if daily_chats:
                        # Add each chat to the list
                        all_chats.extend(daily_chats)
                        print(f"Fetched {len(daily_chats)} chats for {current_date.date()}")
                except Exception as e:
                    print(f"Error fetching {current_date.date()}: {str(e)}")
                
                current_date += timedelta(days=1)
        
        # Fetch both periods
        fetch_range(self.prev_start, self.prev_end, "previous")
        fetch_range(self.current_start, self.current_end, "current")
        
        # Create DataFrame and ensure no duplicate columns
        df = pd.DataFrame(all_chats)
        
        # Convert timestamp columns
        timestamp_columns = ['started', 'ended', 'accepted']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        return df
    
    def analyze_trends(self) -> Dict:
        """Analyze trends by school"""
        trends = {}
        
        for school in sp_ask_school_dict:
            school_name = school['school']['short_name']
            school_queues = school['school']['queues']
            
            if not school_queues:
                continue
            
            try:
                # Filter chats for this school
                school_chats = self.df[self.df['queue'].isin(school_queues)].copy()
                if len(school_chats) == 0:
                    continue
                
                # Split into periods
                prev_period = school_chats[
                    (school_chats['started'] >= self.prev_start) & 
                    (school_chats['started'] <= self.prev_end)
                ]
                current_period = school_chats[
                    (school_chats['started'] >= self.current_start) & 
                    (school_chats['started'] <= self.current_end)
                ]
                
                # Calculate monthly stats without creating new columns
                def get_monthly_stats(period_df: pd.DataFrame) -> pd.DataFrame:
                    monthly_stats = (period_df
                        .groupby([
                            period_df['started'].dt.year,
                            period_df['started'].dt.month
                        ])
                        .agg({
                            'id': 'count',
                            'duration': 'mean',
                            'wait': 'mean'
                        })
                        .reset_index())
                    monthly_stats.columns = ['year', 'month', 'chats', 'avg_duration', 'avg_wait']
                    return monthly_stats
                
                prev_monthly = get_monthly_stats(prev_period)
                current_monthly = get_monthly_stats(current_period)
                
                # Calculate changes
                changes = []
                for _, prev_row in prev_monthly.iterrows():
                    current_row = current_monthly[
                        (current_monthly['month'] == prev_row['month'])
                    ]
                    
                    if not current_row.empty:
                        pct_change_chats = ((current_row['chats'].iloc[0] - prev_row['chats']) / prev_row['chats']) * 100
                        pct_change_duration = ((current_row['avg_duration'].iloc[0] - prev_row['avg_duration']) / prev_row['avg_duration']) * 100
                        pct_change_wait = ((current_row['avg_wait'].iloc[0] - prev_row['avg_wait']) / prev_row['avg_wait']) * 100
                        
                        changes.append({
                            'month': prev_row['month'],
                            'prev_volume': int(prev_row['chats']),
                            'current_volume': int(current_row['chats'].iloc[0]),
                            'percent_change_volume': pct_change_chats,
                            'percent_change_duration': pct_change_duration,
                            'percent_change_wait': pct_change_wait
                        })
                
                if changes:
                    trends[school_name] = {
                        'changes': changes,
                        'total_stats': {
                            'prev_period': {
                                'total_chats': len(prev_period),
                                'avg_duration': prev_period['duration'].mean(),
                                'avg_wait': prev_period['wait'].mean()
                            },
                            'current_period': {
                                'total_chats': len(current_period),
                                'avg_duration': current_period['duration'].mean(),
                                'avg_wait': current_period['wait'].mean()
                            }
                        }
                    }
                    
                    # Calculate overall changes
                    if len(prev_period) > 0:
                        trends[school_name]['overall_changes'] = {
                            'volume_change': ((len(current_period) - len(prev_period)) / len(prev_period)) * 100,
                            'duration_change': ((current_period['duration'].mean() - prev_period['duration'].mean()) / prev_period['duration'].mean()) * 100 if prev_period['duration'].mean() != 0 else 0,
                            'wait_change': ((current_period['wait'].mean() - prev_period['wait'].mean()) / prev_period['wait'].mean()) * 100 if prev_period['wait'].mean() != 0 else 0
                        }
                    else:
                        trends[school_name]['overall_changes'] = {
                            'volume_change': 100,
                            'duration_change': 0,
                            'wait_change': 0
                        }
                
            except Exception as e:
                print(f"Error processing {school_name}: {str(e)}")
                continue
        
        return trends

    def generate_report(self):
        """Generate trend analysis report with charts"""
        try:
            trends = self.analyze_trends()
            
            if not trends:
                print("No data available for analysis!")
                return None
                
            # Sort schools by volume change
            sorted_schools = sorted(
                trends.items(),
                key=lambda x: x[1]['overall_changes']['volume_change']
            )
            
            # Create DataFrame for visualization
            chart_data = []
            for school, data in sorted_schools:
                chart_data.append({
                    'School': school,  # Changed from 'school' to 'School'
                    'Change': data['overall_changes']['volume_change'],  # Changed from 'change' to 'Change'
                    'Direction': 'Increase' if data['overall_changes']['volume_change'] > 0 else 'Decrease'  # Changed from 'direction' to 'Direction'
                })
            
            volume_changes = pd.DataFrame(chart_data)
            
            # Check if we have data to visualize
            if len(volume_changes) == 0:
                print("No data available for visualization!")
                return None
                
            # Create visualizations
            fig_volume = px.bar(
                volume_changes,
                x='School',  # Updated column name
                y='Change',  # Updated column name
                color='Direction',  # Updated column name
                title=f'Chat Volume Changes\n({self.prev_start.date()} to {self.prev_end.date()} vs {self.current_start.date()} to {self.current_end.date()})',
                labels={'Change': 'Percent Change', 'School': 'Institution'},
                color_discrete_map={'Increase': 'green', 'Decrease': 'red'}
            )
            
            # Monthly trends
            fig_monthly = go.Figure()
            
            for school, data in trends.items():
                if 'changes' in data and data['changes']:
                    months = [change['month'] for change in data['changes']]
                    changes = [change['percent_change_volume'] for change in data['changes']]
                    
                    fig_monthly.add_trace(
                        go.Scatter(
                            x=months,
                            y=changes,
                            name=school,
                            mode='lines+markers'
                        )
                    )
            
            fig_monthly.update_layout(
                title='Monthly Chat Volume Changes by School',
                xaxis_title='Month',
                yaxis_title='Percent Change',
                xaxis=dict(
                    tickmode='array',
                    ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                    tickvals=list(range(1, 13))
                )
            )
            
            # Generate HTML report
            report_filename = (f"chat_trends_{self.prev_start.date()}_to_{self.current_end.date()}"
                            .replace("-", "")
                            + ".html")
            
            html_content = self._generate_html_report(trends, fig_volume, fig_monthly)
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\nReport generated: {report_filename}")
            return trends
            
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_html_report(self, trends: Dict, fig_volume: go.Figure, 
                            fig_monthly: go.Figure) -> str:
        """Generate HTML report content"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chat Volume Trend Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    max-width: 1200px;
                    margin: auto;
                }}
                .stats {{
                    margin: 20px 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                }}
                .visualization {{
                    margin: 30px 0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                }}
                .decrease {{
                    color: red;
                }}
                .increase {{
                    color: green;
                }}
            </style>
        </head>
        <body>
            <h1>Chat Volume Trend Analysis</h1>
            <h2>Comparing:</h2>
            <p>Previous period: {self.prev_start.date()} to {self.prev_end.date()}</p>
            <p>Current period: {self.current_start.date()} to {self.current_end.date()}</p>
            
            <div class="stats">
                <h3>Summary</h3>
                <table>
                    <tr>
                        <th>School</th>
                        <th>Previous Period<br>Total Chats</th>
                        <th>Current Period<br>Total Chats</th>
                        <th>Volume Change</th>
                        <th>Duration Change</th>
                        <th>Wait Time Change</th>
                    </tr>
                    {self._generate_table_rows(trends)}
                </table>
            </div>
            
            <div id="volumeChart" class="visualization"></div>
            <div id="monthlyChart" class="visualization"></div>
            
            <script>
                {fig_volume.to_json()}
                Plotly.newPlot('volumeChart', figVolume.data, figVolume.layout);
                
                {fig_monthly.to_json()}
                Plotly.newPlot('monthlyChart', figMonthly.data, figMonthly.layout);
            </script>
        </body>
        </html>
        """
    
    def _generate_table_rows(self, trends: Dict) -> str:
        """Generate HTML table rows for trend data"""
        rows = ""
        for school, data in sorted(
            trends.items(), 
            key=lambda x: x[1]['overall_changes']['volume_change']
        ):
            volume_class = 'increase' if data['overall_changes']['volume_change'] > 0 else 'decrease'
            duration_class = 'increase' if data['overall_changes']['duration_change'] > 0 else 'decrease'
            wait_class = 'increase' if data['overall_changes']['wait_change'] > 0 else 'decrease'
            
            rows += f"""
                <tr>
                    <td>{school}</td>
                    <td>{data['total_stats']['prev_period']['total_chats']:,}</td>
                    <td>{data['total_stats']['current_period']['total_chats']:,}</td>
                    <td class="{volume_class}">{data['overall_changes']['volume_change']:.1f}%</td>
                    <td class="{duration_class}">{data['overall_changes']['duration_change']:.1f}%</td>
                    <td class="{wait_class}">{data['overall_changes']['wait_change']:.1f}%</td>
                </tr>
            """
        return rows

    def _process_monthly_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process monthly statistics for a dataframe"""
        if len(df) == 0:
            return pd.DataFrame()
            
        monthly_stats = (df
            .assign(
                year=df['started'].dt.year,
                month=df['started'].dt.month
            )
            .groupby(['year', 'month'])
            .agg({
                'id': 'count',
                'duration': 'mean',
                'wait': 'mean'
            })
            .reset_index()
        )
        
        monthly_stats.columns = ['year', 'month', 'chats', 'avg_duration', 'avg_wait']
        return monthly_stats

    def analyze_trends(self) -> Dict:
        """Analyze trends by school"""
        if self.df is None or len(self.df) == 0:
            print("No data available for analysis")
            return {}
            
        trends = {}
        
        for school in sp_ask_school_dict:
            try:
                school_name = school['school']['short_name']
                school_queues = school['school']['queues']
                
                if not school_queues:
                    continue
                
                # Filter chats for this school
                school_chats = self.df[self.df['queue'].isin(school_queues)].copy()
                if len(school_chats) == 0:
                    continue
                    
                # Split into periods
                prev_period = school_chats[
                    (school_chats['started'] >= self.prev_start) & 
                    (school_chats['started'] <= self.prev_end)
                ]
                
                current_period = school_chats[
                    (school_chats['started'] >= self.current_start) & 
                    (school_chats['started'] <= self.current_end)
                ]
                
                # Process monthly stats
                prev_monthly = self._process_monthly_stats(prev_period)
                current_monthly = self._process_monthly_stats(current_period)
                
                if len(prev_monthly) == 0 or len(current_monthly) == 0:
                    continue
                    
                # Calculate changes
                changes = []
                for _, prev_row in prev_monthly.iterrows():
                    current_row = current_monthly[
                        current_monthly['month'] == prev_row['month']
                    ]
                    
                    if not current_row.empty:
                        changes.append({
                            'month': int(prev_row['month']),
                            'prev_volume': int(prev_row['chats']),
                            'current_volume': int(current_row['chats'].iloc[0]),
                            'percent_change_volume': ((current_row['chats'].iloc[0] - prev_row['chats']) / prev_row['chats']) * 100,
                            'percent_change_duration': ((current_row['avg_duration'].iloc[0] - prev_row['avg_duration']) / prev_row['avg_duration']) * 100 if prev_row['avg_duration'] != 0 else 0,
                            'percent_change_wait': ((current_row['avg_wait'].iloc[0] - prev_row['avg_wait']) / prev_row['avg_wait']) * 100 if prev_row['avg_wait'] != 0 else 0
                        })
                
                if changes:
                    trends[school_name] = {
                        'changes': changes,
                        'total_stats': {
                            'prev_period': {
                                'total_chats': len(prev_period),
                                'avg_duration': prev_period['duration'].mean() if len(prev_period) > 0 else 0,
                                'avg_wait': prev_period['wait'].mean() if len(prev_period) > 0 else 0
                            },
                            'current_period': {
                                'total_chats': len(current_period),
                                'avg_duration': current_period['duration'].mean() if len(current_period) > 0 else 0,
                                'avg_wait': current_period['wait'].mean() if len(current_period) > 0 else 0
                            }
                        }
                    }
                    
                    prev_total = len(prev_period)
                    if prev_total > 0:
                        trends[school_name]['overall_changes'] = {
                            'volume_change': ((len(current_period) - prev_total) / prev_total) * 100,
                            'duration_change': ((current_period['duration'].mean() - prev_period['duration'].mean()) / prev_period['duration'].mean()) * 100 if prev_period['duration'].mean() != 0 else 0,
                            'wait_change': ((current_period['wait'].mean() - prev_period['wait'].mean()) / prev_period['wait'].mean()) * 100 if prev_period['wait'].mean() != 0 else 0
                        }
                    else:
                        trends[school_name]['overall_changes'] = {
                            'volume_change': 100 if len(current_period) > 0 else 0,
                            'duration_change': 0,
                            'wait_change': 0
                        }
                        
            except Exception as e:
                print(f"Error processing {school_name}: {str(e)}")
                continue
        
        return trends

def analyze_date_range_trends(start_date: str, end_date: str):
    """Main function to analyze trends between date ranges"""
    analyzer = DateRangeTrendAnalysis(start_date, end_date)
    return analyzer.generate_report()