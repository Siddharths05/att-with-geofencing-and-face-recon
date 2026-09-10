import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ThemeProvider } from "./ThemeContext";
import LoginScreen from "./screens/LoginScreen";
import AttendanceScreen from "./screens/AttendanceScreen";

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <ThemeProvider>
      <NavigationContainer>
        <Stack.Navigator initialRouteName="Login" screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Attendance" component={AttendanceScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </ThemeProvider>
  );
}