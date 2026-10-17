import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedLayout from '../layouts/ProtectedLayout';
import PublicLayout from '../layouts/PublicLayout';
import DashboardPage from '../pages/DashboardPage';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import ProfilePage from '../pages/ProfilePage';
import SettingsPage from '../pages/SettingsPage';
import AuditLogsPage from '../pages/AuditLogsPage';
import UsersPage from '../pages/UsersPage';
import NotFoundPage from '../pages/NotFoundPage';
import ForbiddenPage from '../pages/ForbiddenPage';
import ErrorPage from '../pages/ErrorPage';
import LandingPage from '../pages/LandingPage';
import EmployeeWorkspacePage from '../pages/EmployeeWorkspacePage';
import InvestigationPage from '../pages/InvestigationPage';
import DocumentsPage from '../pages/DocumentsPage';
import { useAuth } from '../contexts/AuthContext';

function EmployeeRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return user.role_name === 'SentinelAI Administrator' ? <Navigate to="/403" replace /> : <>{children}</>;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/admin/login" replace />;
  return user.role_name === 'SentinelAI Administrator' ? <>{children}</> : <Navigate to="/403" replace />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/employee" element={<EmployeeRoute><EmployeeWorkspacePage /></EmployeeRoute>} />
      <Route element={<PublicLayout />}>
        <Route path="/login" element={<LoginPage portal="employee" />} />
        <Route path="/admin/login" element={<LoginPage portal="administrator" />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/error" element={<ErrorPage />} />
        <Route path="/403" element={<ForbiddenPage />} />
      </Route>

      <Route element={<ProtectedLayout />}>
        <Route path="/investigations/:identifier" element={<ProtectedRoute><InvestigationPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="/audit-logs" element={<ProtectedRoute><AuditLogsPage /></ProtectedRoute>} />
        <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
        <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
