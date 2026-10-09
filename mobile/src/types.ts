export type User = {
  id: number;
  name: string;
  display_name: string;
  roles: string[];
};

export type TeamSummary = {
  team_id: number;
  team_name: string;
  branch: string;
  category: string;
  jersey_number: number;
  standing_position: number | null;
  division_team_count: number;
};

export type PlayerStatistics = {
  weeks: number;
  points: number;
  receptions: number;
  interceptions: number;
  sacks: number;
  tackles: number;
  passes_completed: number;
  passes_attempted: number;
  completion_percentage: number | null;
};

export type PlayerDashboard = {
  player: {
    id: number;
    name: string;
    aka: string | null;
    profile_photo_url: string | null;
  };
  teams: TeamSummary[];
  statistics: PlayerStatistics;
};

export type Team = {
  id: number;
  name: string;
  branch: string;
  category: string;
  logo_url?: string;
};

export type Game = {
  id: number;
  home_team: Team;
  away_team: Team;
  home_score: number | null;
  away_score: number | null;
  week: number;
  field_number: number | null;
  start_time: string | null;
  status: string;
};

export type RefereeGame = Game & {
  official_position: string;
  is_friendly: boolean;
  officials: {user_id: number; display_name: string; position: string; profile_photo_url: string | null}[];
};

export type RefereeProfile = {id: number; name: string; display_name: string; profile_photo_url: string | null};

export type Standing = {
  team_id: number;
  team_name: string;
  team_logo_url?: string;
  wins: number;
  losses: number;
  points_for: number;
  points_against: number;
  point_difference: number;
};

export type Leader = {
  rank?: number;
  passes_completed?: number;
  passes_attempted?: number;
  player_id: number;
  player_name: string;
  player_aka: string | null;
  profile_photo_url: string | null;
  team_id: number;
  team_name: string;
  jersey_number: number;
  value: number;
};

export type Leaderboards = Record<string, Leader[]> & {
  passing_qualification?: {latest_week: number; minimum_attempts: number};
};

