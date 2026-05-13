import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Eye, EyeOff, Mail, Lock, User, Briefcase } from 'lucide-react';
import { authService } from '../services/auth';
import { setToken, setUser } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Input, Label } from '../components/ui/input';
import { Button } from '../components/ui/button';

export default function LoginPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    role: 'student',
    semester: '1',
    section: 'A',
    roll_number: '',
    employee_id: '',
  });
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [loading, setLoading] = useState(false);

  const validateField = (name, value) => {
    switch (name) {
      case 'email':
        if (!value) return 'Email is required';
        if (!/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(value)) {
          return 'Please enter a valid email address';
        }
        return '';
      case 'password':
        if (!value) return 'Password is required';
        if (value.length < 8) return 'Password must be at least 8 characters';
        if (value.length > 20) return 'Password must be less than 20 characters';
        if (!/[A-Z]/.test(value)) return 'Password must contain at least one capital letter';
        if (!/\d/.test(value)) return 'Password must contain at least one number';
        return '';
      case 'confirm_password':
        if (!isLogin && !value) return 'Please confirm your password';
        if (!isLogin && value !== formData.password) return 'Passwords do not match';
        return '';
      case 'full_name':
        if (!isLogin && !value) return 'Full name is required';
        return '';
      case 'roll_number':
        if (!isLogin && formData.role === 'student' && !value) return 'Roll number is required';
        return '';
      case 'semester':
      case 'section':
        if (!isLogin && formData.role === 'student' && !value) {
          return `${name === 'semester' ? 'Semester' : 'Section'} is required`;
        }
        return '';
      default:
        return '';
    }
  };

  const handleChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }));
    if (touched[name]) {
      setErrors(prev => ({ ...prev, [name]: validateField(name, value) }));
    }
  };

  const handleBlur = (name) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    setErrors(prev => ({ ...prev, [name]: validateField(name, formData[name]) }));
  };

  const validateForm = () => {
    const newErrors = {};
    const fieldsToValidate = isLogin
      ? ['email', 'password']
      : ['email', 'password', 'confirm_password', 'full_name', ...(formData.role === 'student' ? ['semester', 'section', 'roll_number'] : [])];

    fieldsToValidate.forEach(field => {
      const error = validateField(field, formData[field]);
      if (error) newErrors[field] = error;
    });

    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    const validationErrors = validateForm();

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setTouched(
        Object.keys(validationErrors).reduce((acc, key) => ({ ...acc, [key]: true }), {})
      );
      return;
    }

    setLoading(true);

    try {
      if (isLogin) {
        const data = await authService.login(formData.email, formData.password);
        setToken(data.access_token);
        setUser(data.user);
        navigate('/dashboard');
      } else {
        const registerData = {
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          role: formData.role,
        };

        if (formData.role === 'student') {
          registerData.semester = parseInt(formData.semester);
          registerData.section = formData.section;
          registerData.roll_number = formData.roll_number;
        }

        await authService.register(registerData);
        setIsLogin(true);
        setFormData(prev => ({ ...prev, password: '' }));
      }
    } catch (err) {
      setSubmitError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setIsLogin(!isLogin);
    setErrors({});
    setTouched({});
    setSubmitError('');
    setFormData(prev => ({ ...prev, password: '', confirm_password: '' }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-50 via-white to-indigo-50 dark:from-gray-950 dark:to-gray-900 px-4 py-8">
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-500/25 mb-4">
            <GraduationCap className="h-8 w-8 text-white" strokeWidth={2} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
            Academic Portal
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Department of Computer Science & Engineering
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex mb-6 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
              isLogin
                ? 'bg-white dark:bg-gray-700 text-violet-600 dark:text-violet-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
              !isLogin
                ? 'bg-white dark:bg-gray-700 text-violet-600 dark:text-violet-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            Register
          </button>
        </div>

        <Card className="border-gray-200 dark:border-gray-800 shadow-xl shadow-gray-200/50 dark:shadow-none">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Submit Error */}
              {submitError && (
                <div
                  role="alert"
                  className="p-3 text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                >
                  {submitError}
                </div>
              )}

              {/* Registration Fields */}
              {!isLogin && (
                <>
                  {/* Role Selection */}
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => handleChange('role', 'student')}
                      className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 ${
                        formData.role === 'student'
                          ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <Briefcase className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">Student</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleChange('role', 'faculty')}
                      className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 ${
                        formData.role === 'faculty'
                          ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <User className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">Faculty</span>
                    </button>
                  </div>

                  {/* Full Name */}
                  <div className="space-y-2">
                    <Label htmlFor="full_name" className="text-gray-700 dark:text-gray-300">
                      Full Name
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                      <Input
                        id="full_name"
                        type="text"
                        placeholder="Enter your full name"
                        value={formData.full_name}
                        onChange={e => handleChange('full_name', e.target.value)}
                        onBlur={() => handleBlur('full_name')}
                        className={`pl-10 ${touched.full_name && errors.full_name ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                        aria-invalid={touched.full_name && errors.full_name ? 'true' : 'false'}
                        aria-describedby={touched.full_name && errors.full_name ? 'full_name-error' : undefined}
                      />
                    </div>
                    {touched.full_name && errors.full_name && (
                      <p id="full_name-error" className="text-xs text-red-600 dark:text-red-400">
                        {errors.full_name}
                      </p>
                    )}
                  </div>

                  {/* Student Fields */}
                  {formData.role === 'student' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="semester" className="text-gray-700 dark:text-gray-300">
                          Semester
                        </Label>
                        <select
                          id="semester"
                          value={formData.semester}
                          onChange={e => handleChange('semester', e.target.value)}
                          onBlur={() => handleBlur('semester')}
                          className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer ${
                            touched.semester && errors.semester ? 'border-red-500 focus-visible:ring-red-500' : ''
                          }`}
                          aria-invalid={touched.semester && errors.semester ? 'true' : 'false'}
                        >
                          {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                            <option key={s} value={s.toString()}>
                              Semester {s}
                            </option>
                          ))}
                        </select>
                        {touched.semester && errors.semester && (
                          <p className="text-xs text-red-600 dark:text-red-400">{errors.semester}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="section" className="text-gray-700 dark:text-gray-300">
                          Section
                        </Label>
                        <select
                          id="section"
                          value={formData.section}
                          onChange={e => handleChange('section', e.target.value)}
                          onBlur={() => handleBlur('section')}
                          className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer ${
                            touched.section && errors.section ? 'border-red-500 focus-visible:ring-red-500' : ''
                          }`}
                          aria-invalid={touched.section && errors.section ? 'true' : 'false'}
                        >
                          {['A', 'B'].map(s => (
                            <option key={s} value={s}>
                              Section {s}
                            </option>
                          ))}
                        </select>
                        {touched.section && errors.section && (
                          <p className="text-xs text-red-600 dark:text-red-400">{errors.section}</p>
                        )}
                      </div>

                      <div className="space-y-2 col-span-2">
                        <Label htmlFor="roll_number" className="text-gray-700 dark:text-gray-300">
                          Roll Number
                        </Label>
                        <Input
                          id="roll_number"
                          type="text"
                          placeholder="e.g., 2024001"
                          value={formData.roll_number}
                          onChange={e => handleChange('roll_number', e.target.value)}
                          onBlur={() => handleBlur('roll_number')}
                          className={touched.roll_number && errors.roll_number ? 'border-red-500 focus-visible:ring-red-500' : ''}
                          aria-invalid={touched.roll_number && errors.roll_number ? 'true' : 'false'}
                        />
                        {touched.roll_number && errors.roll_number && (
                          <p className="text-xs text-red-600 dark:text-red-400">{errors.roll_number}</p>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-gray-700 dark:text-gray-300">
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your.email@cse.edu"
                    value={formData.email}
                    onChange={e => handleChange('email', e.target.value)}
                    onBlur={() => handleBlur('email')}
                    className={`pl-10 ${touched.email && errors.email ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                    aria-invalid={touched.email && errors.email ? 'true' : 'false'}
                    aria-describedby={touched.email && errors.email ? 'email-error' : undefined}
                  />
                </div>
                {touched.email && errors.email && (
                  <p id="email-error" className="text-xs text-red-600 dark:text-red-400">
                    {errors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-gray-700 dark:text-gray-300">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="8-20 characters"
                    value={formData.password}
                    onChange={e => handleChange('password', e.target.value.slice(0, 20))}
                    onBlur={() => handleBlur('password')}
                    className={`pl-10 pr-10 ${touched.password && errors.password ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                    aria-invalid={touched.password && errors.password ? 'true' : 'false'}
                    aria-describedby={touched.password && errors.password ? 'password-error' : undefined}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer transition-colors"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {touched.password && errors.password && (
                  <p id="password-error" className="text-xs text-red-600 dark:text-red-400">
                    {errors.password}
                  </p>
                )}
              </div>

              {/* Confirm Password - Only for registration */}
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="confirm_password" className="text-gray-700 dark:text-gray-300">
                    Confirm Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                    <Input
                      id="confirm_password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="Re-enter your password"
                      value={formData.confirm_password}
                      onChange={e => handleChange('confirm_password', e.target.value.slice(0, 20))}
                      onBlur={() => handleBlur('confirm_password')}
                      className={`pl-10 pr-10 ${touched.confirm_password && errors.confirm_password ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
                      aria-invalid={touched.confirm_password && errors.confirm_password ? 'true' : 'false'}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer transition-colors"
                      aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {touched.confirm_password && errors.confirm_password && (
                    <p className="text-xs text-red-600 dark:text-red-400">{errors.confirm_password}</p>
                  )}
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full h-11 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-medium shadow-lg shadow-violet-500/25 transition-all duration-200"
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Processing...
                  </span>
                ) : isLogin ? (
                  'Sign In'
                ) : (
                  'Create Account'
                )}
              </Button>

              {/* Toggle Link */}
              <div className="text-center text-sm">
                <button
                  type="button"
                  onClick={switchMode}
                  className="text-violet-600 dark:text-violet-400 hover:text-violet-700 dark:hover:text-violet-300 font-medium cursor-pointer transition-colors"
                >
                  {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
                </button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
          National Institute of Technology, Srinagar &copy; {new Date().getFullYear()} - All rights reserved.
        </p>
      </div>
    </div>
  );
}
