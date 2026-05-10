import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import { User, Mail, Shield, GraduationCap, Badge, Loader2, CheckCircle, AlertCircle, Lock, KeyRound } from 'lucide-react';
import { authService } from '../services/auth';
import { getUser } from '../lib/api';
import { cn } from '../lib/utils';

const MIN_PASSWORD_LENGTH = 8;

export default function ProfilePage() {
  const navigate = useNavigate();
  const user = getUser();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});
  const [success, setSuccess] = useState(false);
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const data = await authService.getCurrentUser();
      setProfile(data);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
      // Fallback to stored user data
      setProfile(user);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }

    if (!formData.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (formData.newPassword.length < MIN_PASSWORD_LENGTH) {
      newErrors.newPassword = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setChanging(true);
    setSuccess(false);
    setErrors({});

    try {
      await authService.changePassword(formData.currentPassword, formData.newPassword);
      setSuccess(true);

      // Clear form
      setFormData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });

      // Redirect to login after 2 seconds
      setTimeout(() => {
        authService.logout();
        navigate('/login');
      }, 2000);

    } catch (err) {
      setErrors({
        submit: err.message || 'Failed to change password. Please check your current password.'
      });
    } finally {
      setChanging(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>
        <p className="text-muted-foreground">
          Manage your account settings and security
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Profile Information Card */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              {/* Full Name */}
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs uppercase tracking-wide">Full Name</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{profile?.full_name || 'N/A'}</span>
                </div>
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs uppercase tracking-wide">Email</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{profile?.email || 'N/A'}</span>
                </div>
              </div>

              {/* Role */}
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs uppercase tracking-wide">Role</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium capitalize">{profile?.role || 'N/A'}</span>
                </div>
              </div>

              {/* Department */}
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs uppercase tracking-wide">Department</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                  <Badge className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{profile?.department || 'N/A'}</span>
                </div>
              </div>

              {/* Student-specific fields */}
              {profile?.role === 'student' && (
                <>
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wide">Roll Number</Label>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                      <Badge className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{profile?.roll_number || 'N/A'}</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wide">Semester</Label>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                      <GraduationCap className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{profile?.semester || 'N/A'}</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs uppercase tracking-wide">Section</Label>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                      <span className="font-bold px-2 py-1 rounded bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
                        {profile?.section || 'N/A'}
                      </span>
                    </div>
                  </div>
                </>
              )}

              {/* Faculty-specific fields */}
              {profile?.role === 'faculty' && (
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase tracking-wide">Employee ID</Label>
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                    <Badge className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{profile?.employee_id || 'N/A'}</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Security Settings Card */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              Security Settings
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Change your password to keep your account secure
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="max-w-md space-y-4">
              {/* Current Password */}
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="currentPassword"
                    type="password"
                    placeholder="Enter current password"
                    value={formData.currentPassword}
                    onChange={(e) => handleInputChange('currentPassword', e.target.value)}
                    className={cn(
                      "pl-10",
                      errors.currentPassword && "border-red-500 focus:border-red-500"
                    )}
                  />
                </div>
                {errors.currentPassword && (
                  <p className="text-xs text-red-600">{errors.currentPassword}</p>
                )}
              </div>

              {/* New Password */}
              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="Enter new password"
                    value={formData.newPassword}
                    onChange={(e) => handleInputChange('newPassword', e.target.value)}
                    className={cn(
                      "pl-10",
                      errors.newPassword && "border-red-500 focus:border-red-500"
                    )}
                  />
                </div>
                {errors.newPassword && (
                  <p className="text-xs text-red-600">{errors.newPassword}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Minimum {MIN_PASSWORD_LENGTH} characters
                </p>
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="Confirm new password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className={cn(
                      "pl-10",
                      errors.confirmPassword && "border-red-500 focus:border-red-500"
                    )}
                  />
                </div>
                {errors.confirmPassword && (
                  <p className="text-xs text-red-600">{errors.confirmPassword}</p>
                )}
              </div>

              {/* Success Message */}
              {success && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                  <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <p className="text-sm text-green-800 dark:text-green-300">
                    Password changed successfully! Redirecting to login...
                  </p>
                </div>
              )}

              {/* Error Message */}
              {errors.submit && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  <p className="text-sm text-red-800 dark:text-red-300">{errors.submit}</p>
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={changing}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
              >
                {changing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Changing Password...
                  </>
                ) : (
                  <>
                    <KeyRound className="h-4 w-4 mr-2" />
                    Change Password
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
