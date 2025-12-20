// Auto-generated TypeScript types from models.yaml
// DO NOT EDIT MANUALLY

export interface User {
  id: number;
  telegram_id: number;
  is_admin?: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  telegram_id: number;
  is_admin?: boolean;
}

export interface UserUpdate {
  telegram_id: number;
  is_admin?: boolean;
}

export interface UserRead {
  id: number;
  telegram_id: number;
  is_admin?: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserRegisteredEvent {
  user_id: number;
  email: string;
  timestamp: string;
}

export interface CommandReceived {
  command: string;
  args: string[];
  user_id: number;
  timestamp: string;
}

export interface CommandReceivedCreate {
  command: string;
  args: string[];
  user_id: number;
  timestamp: string;
}
