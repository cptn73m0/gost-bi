import React from "react";
import { NavigationContainer, DefaultTheme, DarkTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import { useColorScheme, Text, View, StyleSheet, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

const Tab = createBottomTabNavigator();

function DashboardScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Сводка показателей</Text>
        <View style={styles.kpiRow}>
          <KPICard label="Выручка" value="1 247 млн ₽" trend="+8.2%" positive />
          <KPICard label="Заказы" value="8 420" trend="+5.1%" positive />
        </View>
        <View style={styles.kpiRow}>
          <KPICard label="Средний чек" value="148 100 ₽" trend="-1.3%" positive={false} />
          <KPICard label="Клиенты" value="3 842" trend="+12.4%" positive />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function KPICard({ label, value, trend, positive }: { label: string; value: string; trend: string; positive: boolean }) {
  return (
    <View style={styles.kpiCard}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
      <Text style={[styles.kpiTrend, { color: positive ? "#00875a" : "#de350b" }]}>{trend}</Text>
    </View>
  );
}

function ReportsScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>ГОСТ-отчёты</Text>
    </SafeAreaView>
  );
}

function ProfileScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Профиль</Text>
    </SafeAreaView>
  );
}

export default function App() {
  const scheme = useColorScheme();
  return (
    <NavigationContainer theme={scheme === "dark" ? DarkTheme : DefaultTheme}>
      <StatusBar style={scheme === "dark" ? "light" : "dark"} />
      <Tab.Navigator screenOptions={{ headerShown: false }}>
        <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ tabBarLabel: "Дашборды" }} />
        <Tab.Screen name="Reports" component={ReportsScreen} options={{ tabBarLabel: "Отчёты" }} />
        <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarLabel: "Профиль" }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  scroll: { padding: 16 },
  title: { fontSize: 22, fontWeight: "700", color: "#172b4d", marginBottom: 20 },
  kpiRow: { flexDirection: "row", gap: 12, marginBottom: 12 },
  kpiCard: { flex: 1, backgroundColor: "#f4f5f7", borderRadius: 10, padding: 16 },
  kpiLabel: { fontSize: 11, color: "#758195", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 },
  kpiValue: { fontSize: 22, fontWeight: "700", color: "#172b4d" },
  kpiTrend: { fontSize: 12, fontWeight: "600", marginTop: 4 },
});
