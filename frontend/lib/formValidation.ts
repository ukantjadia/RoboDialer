export type FormData = {
  username: string;
  email: string;
  linkedin: string;
  password: string;
  confirmPassword: string;
  gdpr: boolean;
  isStudent: boolean;
};

export type FormErrors = Partial<Record<keyof FormData, string>>;

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
const linkedinRegex = /^https:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-_%]+\/?$/;

export function validateForm(data: FormData, isSignup: boolean): FormErrors {
  const errors: FormErrors = {};

  if (isSignup) {
    if (!data.username.trim()) {
      errors.username = "Username is required.";
    } else if (!usernameRegex.test(data.username)) {
      errors.username = "Username must be 3–20 characters, letters, numbers, or underscores.";
    }

    if (!data.email.trim()) {
      errors.email = "Email is required.";
    } else if (!emailRegex.test(data.email)) {
      errors.email = "Enter a valid email address.";
    }

    if (data.linkedin && !linkedinRegex.test(data.linkedin)) {
      errors.linkedin = "Enter a valid LinkedIn profile URL.";
    }

    if (data.password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }

    if (data.confirmPassword !== data.password) {
      errors.confirmPassword = "Passwords do not match.";
    }

    if (!data.gdpr) {
      errors.gdpr = "You must accept the terms.";
    }
  } else {
    if (!data.email.trim()) {
      errors.email = "Email is required.";
    } else if (!emailRegex.test(data.email)) {
      errors.email = "Enter a valid email address.";
    }

    if (!data.password) {
      errors.password = "Password is required.";
    }
  }

  return errors;
}

export function validateField(id: keyof FormData, value: string, allData: FormData): string | undefined {
  return validateForm({ ...allData, [id]: value }, true)[id];
}
