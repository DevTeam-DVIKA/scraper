import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useExternalAuth } from "../context/ExternalAuthContext";
import { usePhoneAuth } from "../context/PhoneAuthContext";
import PuzzleSlider from "../../components/puzzleSlider/PuzzleSlider";
import { Mail, Lock, Phone, Eye, EyeOff, Loader2, AlertCircle, Check } from "lucide-react";
import { FcGoogle } from "react-icons/fc";
import { FaLinkedinIn } from "react-icons/fa";

const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
const validatePhone = (phone) => /^\d{10}$/.test(phone);

function getUserFriendlyError(err) {
  if (!err) return null;
  if (typeof err === "string") return err;
  if (err.response?.data?.error) return err.response.data.error;
  if (err.code) {
    switch (err.code) {
      case "auth/user-not-found":
        return (
          <>
            No account found.{" "}
            <Link to="/sign-up" className="text-blue-600 underline font-semibold">Sign up here</Link>.
          </>
        );
      case "auth/wrong-password":
        return "Incorrect password. Try again or reset your password.";
      case "auth/too-many-requests":
        return "Too many attempts. Please try again later or reset your password.";
      case "auth/invalid-email":
        return "Invalid email address. Please check and try again.";
      case "auth/email-already-in-use":
        return "This email is already registered. Please log in.";
      case "auth/network-request-failed":
        return "Network error. Please check your internet connection and try again.";
      default:
        return "Sign-in failed. Please try again or contact support.";
    }
  }
  if (err.message) return err.message;
  return "Something went wrong. Please try again or contact support.";
}

export default function SignIn() {
  const {
    loginWithEmail, showGoogleOneTap, loginWithLinkedIn,
    requestOtpForSignIn, verifyOtpForSignIn,
    authError, clearAuthError, fetchUserData,
  } = useExternalAuth();
  const { loading: phoneLoading, error: phoneError, sendOtp, verifyOtp } = usePhoneAuth();
  const navigate = useNavigate();

  const [selectedMethod, setSelectedMethod] = useState("email_password");
  const [emailPass, setEmailPass] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [otpStep, setOtpStep] = useState("send");
  const [otpData, setOtpData] = useState({ countryCode: "+91", phone: "", email: "", otp: "" });
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [linkedinLoading, setLinkedInLoading] = useState(false);
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [pendingLogin, setPendingLogin] = useState(null);

  const isLoading = emailLoading || googleLoading || linkedinLoading || phoneLoading;

  // --- Email/password login ---
  const handleEmailSignIn = (e) => {
    e.preventDefault();
    let newErrors = {};
    setGeneralError(null);
    if (!emailPass.email) newErrors.email = "Email is required";
    else if (!validateEmail(emailPass.email)) newErrors.email = "Invalid email";
    if (!emailPass.password) newErrors.password = "Password is required";
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    setShowCaptcha(true);
    setPendingLogin({ ...emailPass });
  };

  const handleCaptchaSuccess = async () => {
    setEmailLoading(true);
    setGeneralError(null);
    try {
      await loginWithEmail(pendingLogin.email, pendingLogin.password);
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setGeneralError(getUserFriendlyError(err));
    } finally {
      setEmailLoading(false);
      setShowCaptcha(false);
      setPendingLogin(null);
    }
  };

  // --- Google sign in ---
  const handleGoogleSignIn = async () => {
    setGoogleLoading(true);
    setGeneralError(null);
    setErrors({});
    if (clearAuthError) clearAuthError();
    try {
      await showGoogleOneTap();
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setGeneralError(getUserFriendlyError(err));
    } finally {
      setGoogleLoading(false);
    }
  };

  // --- LinkedIn sign in ---
  const linkedInWindowRef = useRef(null);
  const handleLinkedInSignIn = async () => {
    setLinkedInLoading(true);
    setGeneralError(null);
    setErrors({});
    if (clearAuthError) clearAuthError();
    try {
      if (linkedInWindowRef.current && !linkedInWindowRef.current.closed) {
        linkedInWindowRef.current.focus();
      } else {
        linkedInWindowRef.current = window.open(
          "", "LinkedInAuth",
          `width=600,height=600,top=${window.screen.height / 2 - 300},left=${window.screen.width / 2 - 300}`
        );
        setTimeout(() => { loginWithLinkedIn(); }, 200);
      }
    } catch (err) {
      setGeneralError(getUserFriendlyError(err));
      setLinkedInLoading(false);
    }
  };

  useEffect(() => {
    const interval = setInterval(() => {
      if (linkedInWindowRef.current && linkedInWindowRef.current.closed) {
        setLinkedInLoading(false);
      }
    }, 400);
    return () => clearInterval(interval);
  }, []);

  // --- Email OTP Sign In Flow ---
 
const handleSendEmailOtp = async () => {
  let newErrors = {};
  setGeneralError(null);

  if (!validateEmail(otpData.email)) newErrors.email = "Enter valid email";
  if (Object.keys(newErrors).length) {
    setErrors(newErrors);
    return;
  }
  setErrors({});
  if (clearAuthError) clearAuthError();
  setEmailLoading(true);

  try {
    await requestOtpForSignIn(otpData.email.trim().toLowerCase());
    setOtpStep("verify");
    // CLEAR any error!
    setGeneralError(null);
  } catch (err) {
    const errorMessage = typeof err === "string"
      ? err
      : err?.response?.data?.error || err?.message || "";
    if (errorMessage.toLowerCase().includes("name is required")) {
      setGeneralError(
        <>
          No account found.{" "}
          <Link to="/sign-up" className="text-blue-600 underline font-semibold">
            Sign up here
          </Link>.
        </>
      );
    } else {
      setGeneralError(getUserFriendlyError(err));
    }
  } finally {
    setEmailLoading(false);
  }
};

  const handleVerifyEmailOtp = async () => {
    setGeneralError(null);
    if (!otpData.otp || otpData.otp.length < 6) {
      setErrors({ otp: "Please enter the 6-digit OTP" });
      return;
    }
    setErrors({});
    setEmailLoading(true);
    try {
      await verifyOtpForSignIn(otpData.email, otpData.otp);
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    } finally {
      setEmailLoading(false);
    }
  };

  // --- Mobile OTP login (left as-is) ---
  const handleSendMobileOtp = async () => {
    let newErrors = {};
    setGeneralError(null);
    if (!validatePhone(otpData.phone)) newErrors.phone = "Enter valid 10-digit phone";
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    if (clearAuthError) clearAuthError();
    try {
      await sendOtp(`${otpData.countryCode}${otpData.phone}`);
      setOtpStep("verify");
    } catch (err) {
      setGeneralError(getUserFriendlyError(err));
    }
  };

  const handleVerifyMobileOtp = async () => {
    if (!otpData.otp || otpData.otp.length < 6) {
      setErrors({ otp: "Enter 6-digit OTP" });
      return;
    }
    setErrors({});
    setGeneralError(null);
    if (clearAuthError) clearAuthError();
    try {
      await verifyOtp(otpData.otp);
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setGeneralError(getUserFriendlyError(err));
    }
  };

  useEffect(() => { if (phoneError) setGeneralError(phoneError.message); }, [phoneError]);
  useEffect(() => {
    setErrors({});
    setGeneralError(null);
    setOtpStep("send");
    setOtpData({ countryCode: "+91", phone: "", email: "", otp: "" });
    setShowCaptcha(false);
    setPendingLogin(null);
    setEmailPass({ email: "", password: "" });
    if (clearAuthError) clearAuthError();
  }, [selectedMethod]);
  const clearInputErrors = () => { setErrors({}); setGeneralError(null); if (clearAuthError) clearAuthError(); };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-2xl bg-white p-6 sm:p-8 rounded-2xl shadow-xl">
        <div className="flex justify-center items-center mb-6 bg-blue-100 rounded-full h-20 w-20 mx-auto">
          <img src="/logo.png" className="object-contain h-16 w-16" alt="DVIKA Logo" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-6">
          Sign In
        </h2>

        {(generalError || authError) && (
          <div
            className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2"
            role="alert"
            tabIndex={-1}
          >
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="text-sm text-red-600">{generalError || getUserFriendlyError(authError)}</div>
          </div>
        )}

        <div className="flex justify-center gap-4 mb-8">
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${
              selectedMethod === "google"
                ? "border-blue-500 bg-blue-50 shadow-md scale-105"
                : "border-gray-200 hover:border-blue-300"
            }`}
            onClick={handleGoogleSignIn}
            aria-label="Sign in with Google"
            type="button"
            disabled={isLoading}
          >
            <FcGoogle size={24} />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${
              selectedMethod === "linkedin"
                ? "border-blue-500 bg-blue-50 shadow-md scale-105"
                : "border-gray-200 hover:border-blue-300"
            }`}
            onClick={handleLinkedInSignIn}
            aria-label="Sign in with LinkedIn"
            type="button"
            disabled={isLoading}
          >
            <FaLinkedinIn size={24} className="text-blue-700" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${
              selectedMethod === "dvika_otp"
                ? "border-blue-500 bg-blue-50 shadow-md scale-105"
                : "border-gray-200 hover:border-blue-300"
            }`}
            onClick={() => setSelectedMethod("dvika_otp")}
            aria-label="Sign in with DVIKA OTP"
            type="button"
            disabled={isLoading}
          >
            <img src="/favicon.png" alt="DVIKA OTP" className="h-7 w-7" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${
              selectedMethod === "mobile_otp"
                ? "border-blue-500 bg-blue-50 shadow-md scale-105"
                : "border-gray-200 hover:border-blue-300"
            }`}
            onClick={() => setSelectedMethod("mobile_otp")}
            aria-label="Sign in with Mobile OTP"
            type="button"
            disabled={isLoading}
          >
            <Phone size={24} className="text-green-600" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${
              selectedMethod === "email_password"
                ? "border-blue-500 bg-blue-50 shadow-md scale-105"
                : "border-gray-200 hover:border-blue-300"
            }`}
            onClick={() => setSelectedMethod("email_password")}
            aria-label="Sign in with Email/Password"
            type="button"
            disabled={isLoading}
          >
            <Mail size={24} className="text-pink-600" />
          </button>
        </div>

        {selectedMethod === "dvika_otp" && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">
              Sign In with DVIKA OTP
            </h2>
            {otpStep === "send" ? (
              <>
                <div>
                  <label htmlFor="emailotp" className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <div className="relative">
                    <input
                      id="emailotp"
                      name="emailotp"
                      type="email"
                      value={otpData.email}
                      onChange={e => {
                        setOtpData(p => ({ ...p, email: e.target.value }));
                        clearInputErrors();
                      }}
                      className={`block w-full pl-10 pr-3 py-3 border ${
                        errors.email ? "border-red-300 bg-red-50" : "border-gray-300"
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                      placeholder="Enter your email"
                      autoFocus
                      aria-invalid={!!errors.email}
                    />
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  </div>
                  {errors.email && (
                    <p id="email-error" className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="h-4 w-4 mr-1" />
                      {errors.email}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleSendEmailOtp}
                  disabled={isLoading}
                  className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
                >
                  {emailLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                  ) : (
                    <Mail className="w-4 h-4 mr-2 text-white" />
                  )}
                  Send OTP
                </button>
              </>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    We sent a 6-digit code to{" "}
                    <span className="font-medium text-gray-900">{otpData.email}</span>
                  </p>
                </div>
                <div>
                  <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2 text-center">
                    OTP Code *
                  </label>
                  <input
                    id="otp"
                    name="otp"
                    type="text"
                    value={otpData.otp}
                    onChange={e => {
                      setOtpData(p => ({ ...p, otp: e.target.value.replace(/[^0-9]/g, "") }));
                      clearInputErrors();
                    }}
                    maxLength={6}
                    className={`block w-full px-4 py-3 border ${
                      errors.otp ? "border-red-400 bg-red-50" : "border-gray-300"
                    } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm text-center text-xl tracking-widest font-semibold transition-all duration-150`}
                    placeholder="000000"
                    disabled={isLoading}
                    aria-invalid={!!errors.otp}
                  />
                  {errors.otp && (
                    <p id="otp-error" className="mt-2 text-sm text-red-600 flex items-center justify-center">
                      <AlertCircle className="h-4 w-4 mr-1" />
                      {errors.otp}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleVerifyEmailOtp}
                  disabled={isLoading || otpData.otp.length < 6}
                  className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
                >
                  {emailLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                  ) : (
                    <Check className="w-4 h-4 mr-2 text-white" />
                  )}
                  Verify OTP
                </button>
                <div className="mt-4 text-center">
                  <button
                    type="button"
                    onClick={() => {
                      setOtpStep("send");
                      clearInputErrors();
                    }}
                                        className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    Resend OTP
                  </button>
                </div>
              </>
            )}
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Don’t have an account?{" "}
                <Link to="/sign-up" className="font-medium text-blue-600 hover:underline">
                  Sign Up
                </Link>
              </p>
            </div>
          </div>
        )}

        {/* --- Mobile OTP Login Section --- */}
        {selectedMethod === "mobile_otp" && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">
              Sign In with Mobile OTP
            </h2>
            {otpStep === "send" ? (
              <>
                <div>
                  <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                    Mobile Number *
                  </label>
                  <div className="flex space-x-2">
                    <select
                      id="countryCode"
                      name="countryCode"
                      value={otpData.countryCode}
                      onChange={e => {
                        setOtpData(p => ({ ...p, countryCode: e.target.value }));
                        clearInputErrors();
                      }}
                      className={`w-20 px-2 py-3 border ${
                        errors.phone ? "border-red-300 bg-red-50" : "border-gray-300"
                      } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                      disabled={isLoading}
                    >
                      <option value="+91">+91 (India)</option>
                    </select>
                    <div className="relative flex-1">
                      <input
                        id="phone"
                        name="phone"
                        type="tel"
                        value={otpData.phone}
                        onChange={e => {
                          setOtpData(p => ({ ...p, phone: e.target.value.replace(/[^0-9]/g, "") }));
                          clearInputErrors();
                        }}
                        className={`block w-full pl-10 pr-3 py-3 border ${
                          errors.phone ? "border-red-300 bg-red-50" : "border-gray-300"
                        } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                        placeholder="Enter your mobile number"
                        disabled={isLoading}
                        maxLength={10}
                        aria-invalid={!!errors.phone}
                      />
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                    </div>
                  </div>
                  {errors.phone && (
                    <p id="phone-error" className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="h-4 w-4 mr-1" />
                      {errors.phone}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleSendMobileOtp}
                  disabled={isLoading}
                  className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
                >
                  {phoneLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                  ) : (
                    <Phone className="w-4 h-4 mr-2 text-white" />
                  )}
                  Send OTP
                </button>
              </>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    We sent a 6-digit code to{" "}
                    <span className="font-medium text-gray-900">
                      {otpData.countryCode} {otpData.phone}
                    </span>
                  </p>
                </div>
                <div>
                  <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2 text-center">
                    OTP Code *
                  </label>
                  <input
                    id="otp"
                    name="otp"
                    type="text"
                    value={otpData.otp}
                    onChange={e => {
                      setOtpData(p => ({ ...p, otp: e.target.value.replace(/[^0-9]/g, "") }));
                      clearInputErrors();
                    }}
                    maxLength={6}
                    className={`block w-full px-4 py-3 border ${
                      errors.otp ? "border-red-400 bg-red-50" : "border-gray-300"
                    } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm text-center text-xl tracking-widest font-semibold transition-all duration-150`}
                    placeholder="000000"
                    disabled={isLoading}
                    aria-invalid={!!errors.otp}
                  />
                  {errors.otp && (
                    <p id="otp-error" className="mt-2 text-sm text-red-600 flex items-center justify-center">
                      <AlertCircle className="h-4 w-4 mr-1" />
                      {errors.otp}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleVerifyMobileOtp}
                  disabled={isLoading || otpData.otp.length < 6}
                  className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
                >
                  {phoneLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                  ) : (
                    <Check className="w-4 h-4 mr-2 text-white" />
                  )}
                  Verify OTP
                </button>
                <div className="mt-4 text-center">
                  <button
                    type="button"
                    onClick={() => {
                      setOtpStep("send");
                      clearInputErrors();
                    }}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    Resend OTP
                  </button>
                </div>
              </>
            )}
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Don’t have an account?{" "}
                <Link to="/sign-up" className="font-medium text-blue-600 hover:underline">
                  Sign Up
                </Link>
              </p>
            </div>
          </div>
        )}

        {/* --- Email/Password Login Section --- */}
        {selectedMethod === "email_password" && (
          <form onSubmit={handleEmailSignIn} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email ID *
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={emailPass.email}
                  onChange={e => {
                    setEmailPass((p) => ({ ...p, email: e.target.value }));
                    clearInputErrors();
                  }}
                  className={`block w-full pl-10 pr-3 py-3 border ${
                    errors.email ? "border-red-300 bg-red-50" : "border-gray-300"
                  } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your email ID"
                  aria-describedby={errors.email ? "email-error" : undefined}
                  autoFocus
                  aria-invalid={!!errors.email}
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.email && (
                <p id="email-error" className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.email}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password *
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={emailPass.password}
                  onChange={e => {
                    setEmailPass((p) => ({ ...p, password: e.target.value }));
                    clearInputErrors();
                  }}
                  className={`block w-full pl-10 pr-10 py-3 border ${
                    errors.password ? "border-red-300 bg-red-50" : "border-gray-300"
                  } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your password"
                  aria-describedby={errors.password ? "password-error" : undefined}
                  aria-invalid={!!errors.password}
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p id="password-error" className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.password}
                </p>
              )}
            </div>
            <div className="flex justify-end">
              <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:underline">
                Forgot Password?
              </Link>
            </div>
            {!showCaptcha && (
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
              >
                {emailLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                ) : null}
                Sign In
              </button>
            )}
            {showCaptcha && (
              <div>
                <PuzzleSlider onSuccess={handleCaptchaSuccess} />
                <div className="mt-2 text-xs text-gray-500 text-center">
                  Complete the captcha to enable Sign In
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowCaptcha(false);
                    setPendingLogin(null);
                  }}
                  className="w-full mt-3 py-2 rounded-lg bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            )}
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Don’t have an account?{" "}
                <Link to="/sign-up" className="font-medium text-blue-600 hover:underline">
                  Sign Up
                </Link>
              </p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

