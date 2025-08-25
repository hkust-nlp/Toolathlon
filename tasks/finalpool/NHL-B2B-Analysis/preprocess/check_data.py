#!/usr/bin/env python3
"""
NHL Back-to-Back Games Analysis
Analyzes NHL 2024-2025 schedule data to find back-to-back games for each team
and categorizes them by home/away patterns (HA, AH, HH, AA).
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json

def read_nhl_schedule(csv_path):
    """
    Read NHL schedule CSV file
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        DataFrame: Parsed schedule data
    """
    df = pd.read_csv(csv_path)
    
    # Convert Date column to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Sort by date to ensure chronological order
    df = df.sort_values('Date').reset_index(drop=True)
    
    print(f"✅ Loaded {len(df)} games from {csv_path}")
    return df

def get_team_games(df, team_name):
    """
    Get all games for a specific team with home/away information
    
    Args:
        df: Schedule DataFrame
        team_name: Name of the team
        
    Returns:
        List of tuples: (date, is_home) where is_home=True if team plays at home
    """
    games = []
    
    # Find games where team is home
    home_games = df[df['Home'] == team_name][['Date']].copy()
    home_games['is_home'] = True
    
    # Find games where team is visitor (away)
    away_games = df[df['Visitor'] == team_name][['Date']].copy()
    away_games['is_home'] = False
    
    # Combine and sort by date
    all_games = pd.concat([home_games, away_games]).sort_values('Date').reset_index(drop=True)
    
    # Convert to list of tuples
    games = [(row['Date'], row['is_home']) for _, row in all_games.iterrows()]
    
    return games

def find_back_to_back_games(games):
    """
    Find back-to-back games (consecutive days) for a team
    
    Args:
        games: List of (date, is_home) tuples sorted by date
        
    Returns:
        List of back-to-back patterns: ['HA', 'AH', 'HH', 'AA']
    """
    back_to_backs = []
    
    for i in range(len(games) - 1):
        date1, is_home1 = games[i]
        date2, is_home2 = games[i + 1]
        
        # Check if games are exactly 1 day apart
        if (date2 - date1).days == 1:
            # Determine pattern
            if is_home1 and not is_home2:
                pattern = 'HA'  # Home-Away
            elif not is_home1 and is_home2:
                pattern = 'AH'  # Away-Home
            elif is_home1 and is_home2:
                pattern = 'HH'  # Home-Home
            else:  # not is_home1 and not is_home2
                pattern = 'AA'  # Away-Away
                
            back_to_backs.append(pattern)
            
    return back_to_backs

def analyze_all_teams(df):
    """
    Analyze back-to-back games for all teams
    
    Args:
        df: Schedule DataFrame
        
    Returns:
        DataFrame: Analysis results with columns [Team, HA, AH, HH, AA, Total]
    """
    # Get all unique teams
    home_teams = set(df['Home'].unique())
    visitor_teams = set(df['Visitor'].unique())
    all_teams = sorted(home_teams.union(visitor_teams))
    
    print(f"📊 Analyzing back-to-back patterns for {len(all_teams)} teams...")
    
    results = []
    
    for team in all_teams:
        print(f"   Processing {team}...")
        
        # Get all games for this team
        games = get_team_games(df, team)
        
        # Find back-to-back patterns
        patterns = find_back_to_back_games(games)
        
        # Count each pattern type
        ha_count = patterns.count('HA')
        ah_count = patterns.count('AH')
        hh_count = patterns.count('HH')
        aa_count = patterns.count('AA')
        total_count = len(patterns)
        
        results.append({
            'Team': team,
            'HA': ha_count,
            'AH': ah_count,
            'HH': hh_count,
            'AA': aa_count,
            'Total': total_count
        })
        
        print(f"     → {total_count} back-to-back sets (HA:{ha_count}, AH:{ah_count}, HH:{hh_count}, AA:{aa_count})")
    
    # Create DataFrame
    results_df = pd.DataFrame(results)
    
    return results_df

def save_results(results_df, output_path):
    """
    Save analysis results to CSV file
    
    Args:
        results_df: Results DataFrame
        output_path: Output CSV file path
    """
    results_df.to_csv(output_path, index=False)
    print(f"💾 Results saved to {output_path}")
    
    # Display summary
    total_b2b = results_df['Total'].sum()
    total_ha = results_df['HA'].sum()
    total_ah = results_df['AH'].sum()
    total_hh = results_df['HH'].sum()
    total_aa = results_df['AA'].sum()
    
    print(f"\n📈 Analysis Summary:")
    print(f"   Total back-to-back sets across all teams: {total_b2b}")
    print(f"   Home-Away (HA): {total_ha}")
    print(f"   Away-Home (AH): {total_ah}")
    print(f"   Home-Home (HH): {total_hh}")
    print(f"   Away-Away (AA): {total_aa}")
    
    # Show teams with most back-to-backs
    top_teams = results_df.nlargest(5, 'Total')
    print(f"\n🏆 Teams with most back-to-back sets:")
    for _, row in top_teams.iterrows():
        print(f"   {row['Team']}: {row['Total']} sets")

def main():
    """
    Main function to run the NHL back-to-back analysis
    """
    print("🏒 NHL Back-to-Back Games Analysis")
    print("=" * 50)
    
    # File paths
    current_dir = Path(__file__).parent
    csv_path = current_dir / "NHL Regular 2024-2025 - nhl-202425-asplayed_schedule.csv"
    output_path = current_dir.parent / "nhl_b2b_analysis.csv"
    
    try:
        # Read schedule data
        df = read_nhl_schedule(csv_path)
        
        # Analyze all teams
        results_df = analyze_all_teams(df)
        
        # Save results
        save_results(results_df, output_path)
        
        # Display first few rows
        print(f"\n📋 Sample Results:")
        print(results_df.head(10).to_string(index=False))
        
        print(f"\n✅ Analysis completed successfully!")
        print(f"   Output file: {output_path}")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find schedule file at {csv_path}")
        print("   Please ensure the NHL schedule CSV file exists in the preprocess directory.")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False
        
    return True

if __name__ == "__main__":
    main()
