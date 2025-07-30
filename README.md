import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useExternalAuth } from "../context/ExternalAuthContext";
import { usePhoneAuth } from "../context/PhoneAuthContext";
import PuzzleSlider from "../../components/puzzleSlider/PuzzleSlider";
import {
  Mail, Lock, Phone, Eye, EyeOff, Loader2, AlertCircle, User, Check
} from "lucide-react";
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
      case "auth/email-already-in-use":
        return (
          <>
            This email is already registered.{" "}
            <Link to="/sign-in" className="text-blue-600 hover:underline">
              Sign In
            </Link>
          </>
        );
      case "auth/network-request-failed":
        return "Network error. Please check your connection and try again.";
      default:
        return "Sign-up failed. Please try again or contact support.";
    }
  }
  if (err.message) return err.message;
  return "Something went wrong. Please try again or contact support.";
}

export default function SignUp() {
  const {
    registerWithEmail, showGoogleOneTap, loginWithLinkedIn, sendEmailOtp, verifyEmailOtp, fetchUserData
  } = useExternalAuth();
  const { loading: phoneLoading, error: phoneError, sendOtp, verifyOtp } = usePhoneAuth();
  const navigate = useNavigate();

  const [selectedMethod, setSelectedMethod] = useState("email_password");
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    countryCode: "+91",
    phone: "",
    otp: "",
    agreeTerms: false,
  });
  const [otpStep, setOtpStep] = useState("send");
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [linkedinLoading, setLinkedInLoading] = useState(false);
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [pendingRegistration, setPendingRegistration] = useState(null);

  const getPasswordStrength = (password) => {
    let strength = 0;
    if (password.length >= 8) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 20;
    if (!/(.)\1{2,}/.test(password)) strength += 20;
    return strength;
  };
  const passwordStrength = getPasswordStrength(formData.password);

  useEffect(() => {
    setErrors({});
    setGeneralError(null);
    setFormData({
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      countryCode: "+91",
      phone: "",
      otp: "",
      agreeTerms: false,
    });
    setOtpStep("send");
    setShowCaptcha(false);
    setPendingRegistration(null);
    setShowPassword(false);
    setShowConfirmPassword(false);
  }, [selectedMethod]);

  useEffect(() => {
    if (phoneError) setGeneralError(phoneError.message);
  }, [phoneError]);

  const handleEmailSignUp = (e) => {
    e.preventDefault();
    setGeneralError(null);
    const newErrors = {};
    if (!formData.fullName.trim() || formData.fullName.length < 2)
      newErrors.fullName = "Full name must be at least 2 characters";
    if (!formData.email) newErrors.email = "Email is required";
    else if (!validateEmail(formData.email))
      newErrors.email = "Please enter a valid email address";
    if (!formData.password) newErrors.password = "Password is required";
    else if (formData.password.length < 8)
      newErrors.password = "Password must be at least 8 characters";
    else if (passwordStrength < 60)
      newErrors.password = "Please choose a stronger password";
    if (!formData.confirmPassword)
      newErrors.confirmPassword = "Please confirm your password";
    else if (formData.password !== formData.confirmPassword)
      newErrors.confirmPassword = "Passwords do not match";
    if (!formData.agreeTerms)
      newErrors.agreeTerms = "Please agree to the terms and conditions";
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      return;
    }
    setShowCaptcha(true);
    setPendingRegistration({ ...formData });
    setErrors({});
  };

  const handleCaptchaSuccess = async () => {
    setEmailLoading(true);
    setGeneralError(null);
    try {
      await registerWithEmail(
        pendingRegistration.fullName,
        pendingRegistration.email,
        pendingRegistration.password
      );
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
      setShowCaptcha(false);
    } finally {
      setEmailLoading(false);
      setPendingRegistration(null);
    }
  };

  const handleGoogleSignUp = async () => {
    setGoogleLoading(true);
    setGeneralError(null);
    setErrors({});
    try {
      await showGoogleOneTap();
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleLinkedInSignUp = async () => {
    setLinkedInLoading(true);
    setGeneralError(null);
    setErrors({});
    try {
      await loginWithLinkedIn();
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    } finally {
      setLinkedInLoading(false);
    }
  };

  const handleSendEmailOtp = async () => {
    setGeneralError(null);
    const newErrors = {};
    if (!formData.fullName.trim() || formData.fullName.length < 2)
      newErrors.fullName = "Full name must be at least 2 characters";
    if (!validateEmail(formData.email))
      newErrors.email = "Please enter a valid email address";
    if (!formData.agreeTerms)
      newErrors.agreeTerms = "Please agree to the terms and conditions";
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    try {
      await sendEmailOtp(formData.email, formData.fullName);
      setOtpStep("verify");
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    }
  };
const handleVerifyEmailOtp = async () => {
  setGeneralError(null);
  if (!formData.otp || formData.otp.length < 6) {
    setErrors({ otp: "Please enter the 6-digit OTP" });
    return;
  }
  setErrors({});
  try {
    const { token, user } = await verifyEmailOtp(formData.email, formData.otp, formData.fullName);
    localStorage.setItem("externalToken", token);
    setUser(user); // if you maintain user in context
    await fetchUserData();
    navigate("/dashboard", { replace: true });
  } catch (error) {
    setGeneralError(getUserFriendlyError(error));
  }
};


  const handleSendMobileOtp = async () => {
    setGeneralError(null);
    const newErrors = {};
    if (!formData.fullName.trim() || formData.fullName.length < 2)
      newErrors.fullName = "Full name must be at least 2 characters";
    if (!validatePhone(formData.phone))
      newErrors.phone = "Please enter a valid 10-digit phone number";
    if (!formData.agreeTerms)
      newErrors.agreeTerms = "Please agree to the terms and conditions";
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    try {
      const formattedPhone = `${formData.countryCode}${formData.phone}`;
      await sendOtp(formattedPhone, formData.fullName);
      setOtpStep("verify");
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    }
  };

  const handleVerifyMobileOtp = async () => {
    setGeneralError(null);
    if (!formData.otp || formData.otp.length < 6) {
      setErrors({ otp: "Please enter the 6-digit OTP" });
      return;
    }
    setErrors({});
    try {
      await verifyOtp(formData.otp, formData.fullName);
      await fetchUserData();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setGeneralError(getUserFriendlyError(error));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-2xl bg-white p-6 sm:p-8 rounded-2xl shadow-xl">
        <div className="flex justify-center items-center mb-6 bg-blue-100 rounded-full h-20 w-20 mx-auto">
          <img src="/logo.png" className="object-contain h-16 w-16" alt="DVIKA Logo" />
        </div>

        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-6">
          Create Your DVIKA Account
        </h2>

        {generalError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-sm text-red-600">{generalError}</p>
          </div>
        )}

        <div className="flex justify-center gap-4 mb-8">
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${selectedMethod === "google" ? "border-blue-500 bg-blue-50 shadow-md scale-105" : "border-gray-200 hover:border-blue-300"}`}
            onClick={handleGoogleSignUp}
            aria-label="Sign up with Google"
            type="button"
            disabled={googleLoading || linkedinLoading || emailLoading || phoneLoading}
          >
            <FcGoogle size={24} />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${selectedMethod === "linkedin" ? "border-blue-500 bg-blue-50 shadow-md scale-105" : "border-gray-200 hover:border-blue-300"}`}
            onClick={handleLinkedInSignUp}
            aria-label="Sign up with LinkedIn"
            type="button"
            disabled={linkedinLoading || googleLoading || emailLoading || phoneLoading}
          >
            <FaLinkedinIn size={24} className="text-blue-700" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${selectedMethod === "dvika_otp" ? "border-blue-500 bg-blue-50 shadow-md scale-105" : "border-gray-200 hover:border-blue-300"}`}
            onClick={() => setSelectedMethod("dvika_otp")}
            aria-label="Sign up with DVIKA OTP"
            type="button"
          >
            <img src="/favicon.png" alt="DVIKA OTP" className="h-7 w-7" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${selectedMethod === "mobile_otp" ? "border-blue-500 bg-blue-50 shadow-md scale-105" : "border-gray-200 hover:border-blue-300"}`}
            onClick={() => setSelectedMethod("mobile_otp")}
            aria-label="Sign up with Mobile OTP"
            type="button"
          >
            <Phone size={24} className="text-green-600" />
          </button>
          <button
            className={`rounded-full w-12 h-12 flex items-center justify-center border-2 transition-all duration-200 ${selectedMethod === "email_password" ? "border-blue-500 bg-blue-50 shadow-md scale-105" : "border-gray-200 hover:border-blue-300"}`}
            onClick={() => setSelectedMethod("email_password")}
            aria-label="Sign up with Email/Password"
            type="button"
          >
            <Mail size={24} className="text-pink-600" />
          </button>
        </div>

        {selectedMethod === "dvika_otp" && (
          <div className="space-y-5">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                Full Name *
              </label>
              <div className="relative">
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={(e) => setFormData((p) => ({ ...p, fullName: e.target.value }))}
                  className={`block w-full pl-10 pr-3 py-3 border ${errors.fullName ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your full name"
                />
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.fullName && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.fullName}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email *
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                  className={`block w-full pl-10 pr-3 py-3 border ${errors.email ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your email"
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.email}
                </p>
              )}
            </div>
            <div className="flex items-center">
              <input
                id="agreeTerms"
                name="agreeTerms"
                type="checkbox"
                checked={formData.agreeTerms}
                onChange={(e) => setFormData((p) => ({ ...p, agreeTerms: e.target.checked }))}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="agreeTerms" className="ml-2 block text-sm text-gray-600">
                I agree to the{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Terms of Service</Link>{" "}
                and{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Privacy Policy</Link>
              </label>
            </div>
            {errors.agreeTerms && (
              <p className="mt-1 text-sm text-red-600 flex items-center">
                <AlertCircle className="h-4 w-4 mr-1" />
                {errors.agreeTerms}
              </p>
            )}

            {otpStep === "send" ? (
              <button
                onClick={handleSendEmailOtp}
                disabled={emailLoading || googleLoading || linkedinLoading || phoneLoading}
                className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
              >
                {emailLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                ) : (
                  <Mail className="w-4 h-4 mr-2 text-white" />
                )}
                Send OTP
              </button>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    We sent a 6-digit code to <span className="font-medium text-gray-900">{formData.email}</span>
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
                    value={formData.otp}
                    onChange={e => setFormData((p) => ({ ...p, otp: e.target.value.replace(/[^0-9]/g, "") }))}
                    maxLength={6}
                    className={`block w-full px-4 py-3 border ${errors.otp ? "border-red-400 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm text-center text-xl tracking-widest font-semibold transition-all duration-150`}
                    placeholder="000000"
                    aria-describedby={errors.otp ? "otp-error" : undefined}
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
                  disabled={emailLoading || googleLoading || linkedinLoading || phoneLoading || formData.otp.length < 6}
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
                    onClick={() => setOtpStep("send")}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    Resend OTP
                  </button>
                </div>
              </>
            )}

            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Already have an account?{" "}
                <Link to="/sign-in" className="text-blue-600 hover:underline">
                  Sign In
                </Link>
              </p>
            </div>
          </div>
        )}

        {selectedMethod === "mobile_otp" && (
          <div className="space-y-5">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                Full Name *
              </label>
              <div className="relative">
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={e => setFormData((p) => ({ ...p, fullName: e.target.value }))}
                  className={`block w-full pl-10 pr-3 py-3 border ${errors.fullName ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your full name"
                  disabled={phoneLoading}
                />
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.fullName && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.fullName}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                Mobile Number *
              </label>
              <div className="flex space-x-2">
                <select
                  id="countryCode"
                  name="countryCode"
                  value={formData.countryCode}
                  onChange={e => setFormData((p) => ({ ...p, countryCode: e.target.value }))}
                  className={`w-20 px-2 py-3 border ${errors.phone ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  disabled={phoneLoading}
                >
                  <option value="+91">+91 (India)</option>
                </select>
                <div className="relative flex-1">
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={e => setFormData((p) => ({ ...p, phone: e.target.value.replace(/[^0-9]/g, "") }))}
                    className={`block w-full pl-10 pr-3 py-3 border ${errors.phone ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                    placeholder="Enter your mobile number"
                    disabled={phoneLoading}
                    maxLength={10}
                  />
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                </div>
              </div>
              {errors.phone && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.phone}
                </p>
              )}
            </div>
            <div className="flex items-center">
              <input
                id="agreeTerms"
                name="agreeTerms"
                type="checkbox"
                checked={formData.agreeTerms}
                onChange={e => setFormData((p) => ({ ...p, agreeTerms: e.target.checked }))}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                disabled={phoneLoading}
              />
              <label htmlFor="agreeTerms" className="ml-2 block text-sm text-gray-600">
                I agree to the{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Terms of Service</Link>{" "}
                and{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Privacy Policy</Link>
              </label>
            </div>
            {errors.agreeTerms && (
              <p className="mt-1 text-sm text-red-600 flex items-center">
                <AlertCircle className="h-4 w-4 mr-1" />
                {errors.agreeTerms}
              </p>
            )}

            {otpStep === "send" ? (
              <button
                onClick={handleSendMobileOtp}
                disabled={phoneLoading || emailLoading || googleLoading || linkedinLoading}
                className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
              >
                {phoneLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                ) : (
                  <Phone className="w-4 h-4 mr-2 text-white" />
                )}
                Send OTP
              </button>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    We sent a 6-digit code to{" "}
                    <span className="font-medium text-gray-900">
                      {formData.countryCode} {formData.phone}
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
                    value={formData.otp}
                    onChange={e => setFormData((p) => ({ ...p, otp: e.target.value.replace(/[^0-9]/g, "") }))}
                    maxLength={6}
                    className={`block w-full px-4 py-3 border ${errors.otp ? "border-red-400 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm text-center text-xl tracking-widest font-semibold transition-all duration-150`}
                    placeholder="000000"
                    aria-describedby={errors.otp ? "otp-error" : undefined}
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
                  disabled={phoneLoading || emailLoading || googleLoading || linkedinLoading || formData.otp.length < 6}
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
                    onClick={() => setOtpStep("send")}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    Resend OTP
                  </button>
                </div>
              </>
            )}

            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Already have an account?{" "}
                <Link to="/sign-in" className="text-blue-600 hover:underline">
                  Sign In
                </Link>
              </p>
            </div>
          </div>
        )}

        {selectedMethod === "email_password" && (
          <form onSubmit={handleEmailSignUp} className="space-y-5">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                Full Name *
              </label>
              <div className="relative">
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={e => setFormData((p) => ({ ...p, fullName: e.target.value }))}
                  className={`block w-full pl-10 pr-3 py-3 border ${errors.fullName ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your full name"
                />
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.fullName && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.fullName}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email ID *
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData((p) => ({ ...p, email: e.target.value }))}
                  className={`block w-full pl-10 pr-3 py-3 border ${errors.email ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Enter your email ID"
                  aria-describedby={errors.email ? "email-error" : undefined}
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
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
                  value={formData.password}
                  onChange={e => setFormData((p) => ({ ...p, password: e.target.value }))}
                  className={`block w-full pl-10 pr-10 py-3 border ${errors.password ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Minimum 8 characters"
                  aria-describedby={errors.password ? "password-error" : undefined}
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {formData.password && (
                <div className="mt-2">
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          passwordStrength < 40 ? "bg-red-500" : passwordStrength < 60 ? "bg-yellow-500" : "bg-green-500"
                        }`}
                        style={{ width: `${passwordStrength}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-600">
                      {passwordStrength < 40 ? "Weak" : passwordStrength < 60 ? "Moderate" : "Strong"}
                    </span>
                  </div>
                </div>
              )}
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.password}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                Confirm Password *
              </label>
              <div className="relative">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.confirmPassword}
                  onChange={e => setFormData((p) => ({ ...p, confirmPassword: e.target.value }))}
                  className={`block w-full pl-10 pr-10 py-3 border ${errors.confirmPassword ? "border-red-300 bg-red-50" : "border-gray-300"} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm transition-all duration-150`}
                  placeholder="Confirm your password"
                  aria-describedby={errors.confirmPassword ? "confirmPassword-error" : undefined}
                />
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.confirmPassword}
                </p>
              )}
            </div>
            <div className="flex items-center">
              <input
                id="agreeTerms"
                name="agreeTerms"
                type="checkbox"
                checked={formData.agreeTerms}
                onChange={e => setFormData((p) => ({ ...p, agreeTerms: e.target.checked }))}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="agreeTerms" className="ml-2 block text-sm text-gray-600">
                I agree to the{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Terms of Service</Link>{" "}
                and{" "}
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">Privacy Policy</Link>
              </label>
            </div>
            {errors.agreeTerms && (
              <p className="mt-1 text-sm text-red-600 flex items-center">
                <AlertCircle className="h-4 w-4 mr-1" />
                {errors.agreeTerms}
              </p>
            )}
            {!showCaptcha && (
              <button
                type="submit"
                disabled={emailLoading || googleLoading || linkedinLoading || phoneLoading || !formData.agreeTerms}
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
              >
                {emailLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2 text-white" />
                ) : null}
                Create Account
              </button>
            )}
            {showCaptcha && (
              <div>
                <PuzzleSlider onSuccess={handleCaptchaSuccess} />
                <div className="mt-2 text-xs text-gray-500 text-center">
                  Complete the captcha to enable Create Account
                </div>
                <button
                  type="button"
                  onClick={() => setShowCaptcha(false)}
                  className="w-full mt-3 py-2 rounded-lg bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            )}
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Already have an account?{" "}
                <Link to="/sign-in" className="text-blue-600 hover:underline">
                  Sign In
                </Link>
              </p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
