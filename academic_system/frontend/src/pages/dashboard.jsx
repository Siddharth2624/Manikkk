import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, clearAuthSession, getUser } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  Calendar,
  ClipboardList,
  FolderOpen,
  Users,
  Clock,
  CheckCircle,
  BookOpen,
  GraduationCap,
  Activity,
  Shield,
  LogOut,
  AlertCircle,
} from 'lucide-react';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [user] = useState(() => getUser());  // useState keeps stable reference
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    // Set minimal stats immediately so UI renders
    setStats({
      total_users: 0,
      students: 0,
      faculty: 0,
      admins: 1,
    });

    const fetchStats = async () => {
      try {
        if (user.role === 'admin') {
          // Try to fetch stats from backend
          try {
            const data = await api('/admin/stats');
            setStats(data);
          } catch (err) {
            if (err.status === 401) return;
            // Stats fetch failed, using default values
          }
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [user, navigate]);

  const handleLogout = () => {
    clearAuthSession();
    navigate('/login');
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const getDisplayName = () => {
    return user?.full_name || user?.email?.split('@')[0] || 'User';
  };

  const getQuickActions = () => {
    const actions = [
      {
        label: 'Timetable',
        href: '/timetable',
        icon: Calendar,
        color: 'from-blue-500 to-blue-600',
        bg: 'bg-blue-50 dark:bg-blue-950',
        desc: 'View your class schedule'
      },
    ];

    // Faculty-only actions
    if (user?.role === 'faculty') {
      actions.push(
        {
          label: 'Attendance',
          href: '/attendance',
          icon: ClipboardList,
          color: 'from-emerald-500 to-emerald-600',
          bg: 'bg-emerald-50 dark:bg-emerald-950',
          desc: 'Mark attendance'
        },
        {
          label: 'Materials',
          href: '/materials',
          icon: FolderOpen,
          color: 'from-violet-500 to-violet-600',
          bg: 'bg-violet-50 dark:bg-violet-950',
          desc: 'Upload study materials'
        }
      );
    }

    // Student-only materials
    if (user?.role === 'student') {
      actions.push({
        label: 'Materials',
        href: '/materials',
        icon: FolderOpen,
        color: 'from-violet-500 to-violet-600',
        bg: 'bg-violet-50 dark:bg-violet-950',
        desc: 'Access study materials'
      });
    }

    // Admin-only actions
    if (user?.role === 'admin') {
      actions.push({
        label: 'Manage Users',
        href: '/admin/users',
        icon: Users,
        color: 'from-orange-500 to-orange-600',
        bg: 'bg-orange-50 dark:bg-orange-950',
        desc: 'Add, edit, or remove users'
      });
    }

    return actions;
  };

  const getStatCards = () => {
    const baseStats = stats || { total_users: 0, students: 0, faculty: 0, admins: 1 };

    if (user?.role === 'admin') {
      return [
        {
          label: 'Total Users',
          value: baseStats.total_users || 0,
          icon: Users,
          color: 'from-blue-500 to-blue-600',
          textColor: 'text-blue-600 dark:text-blue-400'
        },
        {
          label: 'Students',
          value: baseStats.students || 0,
          icon: GraduationCap,
          color: 'from-emerald-500 to-emerald-600',
          textColor: 'text-emerald-600 dark:text-emerald-400'
        },
        {
          label: 'Faculty',
          value: baseStats.faculty || 0,
          icon: Shield,
          color: 'from-violet-500 to-violet-600',
          textColor: 'text-violet-600 dark:text-violet-400'
        },
        {
          label: 'Admins',
          value: baseStats.admins || 1,
          icon: Activity,
          color: 'from-orange-500 to-orange-600',
          textColor: 'text-orange-600 dark:text-orange-400'
        },
      ];
    }

    if (user?.role === 'student') {
      return [
        {
          label: 'Semester',
          value: `${user?.semester || '-'}`,
          icon: BookOpen,
          color: 'from-blue-500 to-blue-600',
          textColor: 'text-blue-600 dark:text-blue-400'
        },
        {
          label: 'Section',
          value: user?.section || '-',
          icon: Users,
          color: 'from-emerald-500 to-emerald-600',
          textColor: 'text-emerald-600 dark:text-emerald-400'
        },
        {
          label: 'Status',
          value: 'Active',
          icon: CheckCircle,
          color: 'from-violet-500 to-violet-600',
          textColor: 'text-violet-600 dark:text-violet-400'
        },
        {
          label: 'Materials',
          value: 'View',
          icon: FolderOpen,
          color: 'from-orange-500 to-orange-600',
          textColor: 'text-orange-600 dark:text-orange-400'
        },
      ];
    }

    if (user?.role === 'faculty') {
      return [
        {
          label: 'Department',
          value: user?.department || 'CSE',
          icon: Shield,
          color: 'from-violet-500 to-violet-600',
          textColor: 'text-violet-600 dark:text-violet-400'
        },
        {
          label: 'Status',
          value: 'Active',
          icon: CheckCircle,
          color: 'from-emerald-500 to-emerald-600',
          textColor: 'text-emerald-600 dark:text-emerald-400'
        },
        {
          label: 'Attendance',
          value: 'Mark',
          icon: ClipboardList,
          color: 'from-blue-500 to-blue-600',
          textColor: 'text-blue-600 dark:text-blue-400'
        },
        {
          label: 'Materials',
          value: 'Upload',
          icon: FolderOpen,
          color: 'from-orange-500 to-orange-600',
          textColor: 'text-orange-600 dark:text-orange-400'
        },
      ];
    }

    return [];
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Redirecting to login...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            {getGreeting()}, {getDisplayName()}!
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {user?.role === 'student' && `Semester ${user?.semester} • Section ${user?.section}`}
            {user?.role === 'faculty' && `Faculty • ${user?.department || 'Computer Science & Engineering'}`}
            {user?.role === 'admin' && 'System Administrator'}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleLogout}
          className="gap-2"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
          <AlertCircle className="h-5 w-5 text-orange-600 dark:text-orange-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-orange-800 dark:text-orange-300">
              Connection Error
            </p>
            <p className="text-xs text-orange-600 dark:text-orange-400 mt-0.5">
              Unable to connect to the server. Some features may not work.
            </p>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {getStatCards().map((stat, index) => (
          <Card key={index} className="border-gray-200 dark:border-gray-800 hover:shadow-lg transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{stat.label}</p>
                  <p className={`text-3xl font-bold ${stat.textColor} mt-1`}>{stat.value}</p>
                </div>
                <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.color}`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {getQuickActions().map((action, index) => (
            <a
              key={index}
              href={action.href}
              className="group flex items-start space-x-4 p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-violet-300 dark:hover:border-violet-700 hover:shadow-lg transition-all cursor-pointer"
            >
              <div className={`p-2.5 rounded-lg bg-gradient-to-br ${action.color} group-hover:scale-110 transition-transform`}>
                <action.icon className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 dark:text-white">{action.label}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{action.desc}</p>
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Welcome Card for New Users */}
      <Card className="border-violet-200 dark:border-violet-800 bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-950 dark:to-indigo-950">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600">
              <GraduationCap className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
                Welcome to CSE Academic Portal
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                This is your centralized dashboard for managing academic activities.
                Use the quick actions above to navigate to different sections.
              </p>
              {user?.role === 'admin' && (
                <p className="text-sm text-violet-600 dark:text-violet-400 mt-3">
                  Tip: Start by adding faculty members and students through the Manage Users section.
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
