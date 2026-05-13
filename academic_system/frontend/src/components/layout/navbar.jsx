import { Link, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, User, GraduationCap, Calendar, ClipboardList, FolderOpen, Users, Menu, X, LayoutDashboard, BookOpen, Settings, UserPlus, Edit3, FileText } from 'lucide-react';
import { clearAuthSession, getUser } from '../../lib/api';
import { cn } from '../../lib/utils';
import { useState } from 'react';

export function Navbar({ currentRole }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    clearAuthSession();
    navigate('/login');
  };

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, show: true },
    { label: 'Timetable', href: '/timetable', icon: Calendar, show: true },
    {
      label: 'Attendance',
      href: '/attendance',
      icon: ClipboardList,
      show: ['faculty', 'student'].includes(currentRole)  // Faculty and Students only (NOT admin)
    },
    {
      label: 'Reports',
      href: '/faculty/reports',
      icon: FileText,
      show: currentRole === 'faculty'  // Faculty only
    },
    {
      label: 'My Subjects',
      href: '/faculty/subjects',
      icon: BookOpen,
      show: currentRole === 'faculty'  // Faculty only
    },
    {
      label: 'Materials',
      href: '/materials',
      icon: FolderOpen,
      show: ['faculty', 'student'].includes(currentRole)  // No upload for students
    },
    // Admin menu items
    { label: 'Manage Users', href: '/admin/users', icon: Users, show: currentRole === 'admin' },
    { label: 'Assignments', href: '/admin/assignments', icon: UserPlus, show: currentRole === 'admin' },
    { label: 'Timetable Generator', href: '/admin/timetable', icon: Settings, show: currentRole === 'admin' },
    { label: 'Edit Timetable', href: '/admin/timetable/edit', icon: Edit3, show: currentRole === 'admin' },
    { label: 'Profile', href: '/profile', icon: User, show: true },  // All users
  ];

  const isActive = (href) => location.pathname === href;

  return (
    <nav className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur-lg sticky top-0 z-50">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link to="/dashboard" className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600">
            <GraduationCap className="h-5 w-5 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-lg text-gray-900 dark:text-white hidden sm:inline-block">
            CSE Portal
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center space-x-1">
          {navItems.map((item) =>
            item.show ? (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  isActive(item.href)
                    ? 'text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/20'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            ) : null
          )}
        </div>

        {/* User Menu */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 text-sm">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-medium">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0)}
            </div>
            <div className="flex flex-col">
              <span className="font-medium text-gray-900 dark:text-white">{user?.full_name || 'User'}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">{currentRole}</span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="hidden sm:flex items-center justify-center h-9 w-9 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden flex items-center justify-center h-9 w-9 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 cursor-pointer"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
          <div className="px-4 py-4 space-y-2">
            {navItems.map((item) =>
              item.show ? (
                <Link
                  key={item.href}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    'flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all',
                    isActive(item.href)
                      ? 'text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/20'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              ) : null
            )}
            <div className="border-t border-gray-200 dark:border-gray-800 pt-4 mt-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-medium">
                  {user?.full_name?.charAt(0) || user?.email?.charAt(0)}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{user?.full_name || 'User'}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{currentRole}</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
