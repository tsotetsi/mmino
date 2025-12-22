import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Replace with your backend API base URL

const register = async (email, password, username, fullName) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/register`, {
      email,
      password,
      username,
      full_name: fullName,
    });
    return response.data;
  } catch (error) {
    console.error("Registration API error:", error);
    throw error;
  }
};

const login = async (email, password) => {
  try {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    return response.data;
  } catch (error) {
    console.error("Login API error:", error);
    throw error;
  }
};

export { register, login };