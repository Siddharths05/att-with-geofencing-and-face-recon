import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Use your computer's local network IP, NOT "localhost" — a phone/emulator
// can't reach your machine's localhost. Find it with `ipconfig` (Windows)
// or `ifconfig`/`ip addr` (Mac/Linux), e.g. "http://192.168.1.10:8000"
const BASE_URL = "http://192.168.1.9:8000";

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
