export interface User {
  id: string;
  name: string;
  email: string;
  role_id: number;
  role_name: string;
  is_verified: boolean;
  is_active: boolean;
  last_login?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  login_as?: string;
  portal: 'employee' | 'administrator';
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
  requested_role: 'Employee' | 'Manager' | 'HR' | 'Payroll Administrator';
}

export interface RegisterResponse {
  status: 'active' | 'pending_approval';
  message: string;
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
