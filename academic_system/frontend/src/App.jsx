import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import {
  clearAuthSession,
  getToken,
  getTokenExpiresAt,
  getUser,
  isTokenExpired,
  redirectToLogin,
} from './lib/api';
import { Layout } from './components/layout/layout';

// Pages
import LoginPage from './pages/login';
import DashboardPage from './pages/dashboard';
import TimetablePage from './pages/timetable';
import AttendancePage from './pages/attendance';
import MaterialsPage from './pages/materials';
import AdminUsersPage from './pages/admin-users';
import AdminTimetablePage from './pages/admin-timetable';
import AdminEditTimetablePage from './pages/admin/edit-timetable';
import AdminAssignmentsPage from './pages/admin/assignments';
import AdminFacultyAvailabilityPage from './pages/admin/faculty-availability';
import FacultySubjectsPage from './pages/faculty/my-subjects';
import ProfilePage from './pages/profile';
import FacultyReportsPage from './pages/faculty/reports';

// Protected Route Wrapper
function ProtectedRoute({ children, allowedRoles = [] }) {
  const user = getUser();
  const token = getToken();
  const tokenExpired = isTokenExpired(token);

  useEffect(() => {
    if (!token || tokenExpired) {
      clearAuthSession();
    }
  }, [token, tokenExpired]);

  useEffect(() => {
    if (!token || tokenExpired) {
      return undefined;
    }

    const expiresAt = getTokenExpiresAt(token);
    if (!expiresAt) {
      return undefined;
    }

    const timeoutId = window.setTimeout(
      redirectToLogin,
      Math.max(expiresAt - Date.now(), 0)
    );

    return () => window.clearTimeout(timeoutId);
  }, [token, tokenExpired]);

  if (!user || !token || tokenExpired) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Layout currentRole={user.role}>{children}</Layout>;
}

function App() {
  return (
    <Routes>
      {/* Public Route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Navigate to="/dashboard" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/timetable"
        element={
          <ProtectedRoute>
            <TimetablePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/attendance"
        element={
          <ProtectedRoute allowedRoles={['faculty', 'student']}>
            <AttendancePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/materials"
        element={
          <ProtectedRoute>
            <MaterialsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminUsersPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/timetable"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminTimetablePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/timetable/edit"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminEditTimetablePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/assignments"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminAssignmentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/faculty-availability"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminFacultyAvailabilityPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/faculty/subjects"
        element={
          <ProtectedRoute allowedRoles={['faculty']}>
            <FacultySubjectsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/faculty/reports"
        element={
          <ProtectedRoute allowedRoles={['faculty']}>
            <FacultyReportsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
