<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api, { setAuthToken } from "../api";

const router = useRouter();

const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const body = new URLSearchParams();
    body.append("username", username.value);
    body.append("password", password.value);
    const { data } = await api.post("/auth/token", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("access_token", data.access_token);
    setAuthToken(data.access_token);
    router.push({ name: "inventory" });
  } catch (err) {
    error.value = err.response?.data?.detail || "Identifiants invalides";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <v-app>
    <div class="login-hero" />
    <v-main class="d-flex align-center justify-center">
      <v-card class="pa-6" max-width="420">
        <v-card-title class="text-h5 font-weight-bold mb-4">Connexion</v-card-title>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-3">
          {{ error }}
        </v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field v-model="username" label="Nom d'utilisateur" prepend-icon="mdi-account" />
          <v-text-field
            v-model="password"
            label="Mot de passe"
            type="password"
            prepend-icon="mdi-lock"
            class="mt-2"
          />
          <v-btn type="submit" color="primary" block class="mt-4" :loading="loading">Se connecter</v-btn>
        </v-form>
      </v-card>
    </v-main>
  </v-app>
</template>

<style scoped>
.login-hero {
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at 20% 20%, rgba(123, 197, 255, 0.25), transparent 35%),
    radial-gradient(circle at 80% 10%, rgba(98, 167, 255, 0.15), transparent 30%),
    linear-gradient(135deg, rgba(18, 39, 68, 0.9), rgba(18, 39, 68, 0.6));
  opacity: 0.4;
  pointer-events: none;
}
</style>
