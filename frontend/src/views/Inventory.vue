<script setup>
import { onMounted, reactive, ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useTheme } from "vuetify";
import api, { setAuthToken } from "../api";

const router = useRouter();
const storedToken = localStorage.getItem("access_token");
if (storedToken) {
  setAuthToken(storedToken);
}

const loading = ref(false);
const devices = ref([]);
const total = ref(0);
const statuses = ref([]);
const types = ref([]);
const users = ref([]);
const managedUsers = ref([]);

const search = ref("");
const filterStatus = ref(null);
const filterType = ref(null);
const scanInput = ref("");

const deviceDialog = ref(false);
const deleteDialog = ref(false);
const loanDialog = ref(false);
const returnDialog = ref(false);
const detailDialog = ref(false);
const userDialog = ref(false);

const selectedDevice = ref(null);
const deviceForm = reactive({
  inventory_number: "",
  name: "",
  description: "",
  location: "",
  type_id: null,
  status_id: null,
  security_level: "standard",
});
const isEdit = ref(false);

const loanForm = reactive({
  device_id: null,
  borrower: "",
  borrower_display_name: "",
  usage_location: "",
  due_date: "",
  notes: "",
});

const returnForm = reactive({
  device_id: null,
  notes: "",
});

const currentUser = ref({
  username: "dev-user",
  roles: ["admin"], // placeholder; if non-admin, leave empty or remove "admin"
});
const securityLevels = [
  { title: "Standard (tous)", value: "standard" },
  { title: "Avancé (gestionnaire/expert/admin)", value: "avance" },
  { title: "Critique (expert/admin)", value: "critique" },
];
const roleOptions = [
  { title: "Employee", value: "employee" },
  { title: "Gestionnaire", value: "gestionnaire" },
  { title: "Expert", value: "expert" },
  { title: "Admin", value: "admin" },
];
const isAdmin = computed(() => currentUser.value.roles?.includes("admin"));
const adminMode = ref(true);

const theme = useTheme();
const isDark = ref(theme.global.name.value === "darkBlue");

function toggleTheme() {
  const next = isDark.value ? "lightBlue" : "darkBlue";
  theme.global.name.value = next;
  isDark.value = next === "darkBlue";
}

function toggleAdminMode() {
  if (!isAdmin.value) return;
  adminMode.value = !adminMode.value;
}

const isReadOnly = computed(() => !isAdmin.value || !adminMode.value);

watch(
  () => isAdmin.value,
  (val) => {
    if (!val) adminMode.value = false;
  },
  { immediate: true }
);

async function loadCatalog() {
  try {
    const [statusRes, typeRes] = await Promise.all([
      api.get("/catalog/statuses"),
      api.get("/catalog/types"),
    ]);
    statuses.value = statusRes.data;
    types.value = typeRes.data;
    if (!deviceForm.status_id && statuses.value.length) {
      deviceForm.status_id = statuses.value[0].id;
    }
    if (!deviceForm.type_id && types.value.length) {
      deviceForm.type_id = types.value[0].id;
    }
  } catch (err) {
    if (!handleAuthError(err)) {
      console.error("Impossible de charger le catalogue", err);
    }
  }
}

async function loadUsers() {
  try {
    const res = await api.get("/catalog/users");
    users.value = res.data;
  } catch (err) {
    if (!handleAuthError(err)) {
      console.warn("Impossible de charger les utilisateurs de test", err);
    }
  }
}

async function loadManagedUsers() {
  try {
    const res = await api.get("/users");
    managedUsers.value = res.data;
  } catch (err) {
    if (!handleAuthError(err)) {
      console.error("Impossible de charger les rôles utilisateurs", err);
    }
  }
}

async function saveUserRoles(user) {
  try {
    const payload = { display_name: user.display_name, roles: user.roles };
    await api.put(`/users/${user.username}`, payload);
  } catch (err) {
    if (!handleAuthError(err)) {
      console.error("Erreur lors de la mise à jour des rôles", err);
    }
  }
}

async function openUserDialog() {
  userDialog.value = true;
  await loadManagedUsers();
}

async function loadCurrentUser() {
  try {
    const { data } = await api.get("/auth/me");
    currentUser.value = data;
    adminMode.value = data.roles?.includes("admin");
  } catch (err) {
    if (!handleAuthError(err)) {
      console.warn("Impossible de charger l'utilisateur courant (dev mode ?)", err);
    }
  }
}

async function loadDevices() {
  loading.value = true;
  try {
    const params = {
      search: search.value || undefined,
      status_id: filterStatus.value || undefined,
      type_id: filterType.value || undefined,
      limit: 100,
    };
    const { data } = await api.get("/devices", { params });
    devices.value = data.items;
    total.value = data.total;
  } catch (err) {
    if (!handleAuthError(err)) {
      console.error(err);
    }
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  if (isReadOnly.value) return;
  isEdit.value = false;
  Object.assign(deviceForm, {
    inventory_number: "",
    name: "",
    description: "",
    location: "",
    type_id: types.value[0]?.id || null,
    status_id: statuses.value[0]?.id || null,
    security_level: "standard",
  });
  deviceDialog.value = true;
}

function openEditDialog(device) {
  if (isReadOnly.value) return;
  isEdit.value = true;
  selectedDevice.value = device;
  Object.assign(deviceForm, {
    inventory_number: device.inventory_number,
    name: device.name,
    description: device.description,
    location: device.location,
    type_id: device.type.id,
    status_id: device.status.id,
    security_level: device.security_level || "standard",
  });
  deviceDialog.value = true;
}

async function saveDevice() {
  if (isReadOnly.value) return;
  const payload = { ...deviceForm };
  if (isEdit.value && selectedDevice.value) {
    await api.put(`/devices/${selectedDevice.value.id}`, payload);
  } else {
    await api.post("/devices", payload);
  }
  deviceDialog.value = false;
  await loadDevices();
}

async function confirmDelete(device) {
  if (isReadOnly.value) return;
  selectedDevice.value = device;
  deleteDialog.value = true;
}

async function deleteDevice() {
  if (!selectedDevice.value) return;
  if (isReadOnly.value) return;
  await api.delete(`/devices/${selectedDevice.value.id}`);
  deleteDialog.value = false;
  selectedDevice.value = null;
  await loadDevices();
}

function openLoanModal(device) {
  if (!canLoan(device)) return;
  selectedDevice.value = device;
  Object.assign(loanForm, {
    device_id: device.id,
    borrower: "",
    borrower_display_name: "",
    usage_location: "",
    due_date: "",
    notes: "",
  });
  loanDialog.value = true;
}

function openReturnModal(device) {
  if (!canReturn(device)) return;
  selectedDevice.value = device;
  Object.assign(returnForm, {
    device_id: device.id,
    notes: "",
  });
  returnDialog.value = true;
}

async function submitLoan() {
  if (isReadOnly.value) return;
  const payload = { ...loanForm, due_date: loanForm.due_date || null };
  await api.post("/loans/loan", payload);
  loanDialog.value = false;
  await loadDevices();
}

async function submitReturn() {
  if (isReadOnly.value) return;
  await api.post("/loans/return", returnForm);
  returnDialog.value = false;
  await loadDevices();
}

function openDetail(device) {
  if (!device) return;
  const payload = device.raw ?? device;
  selectedDevice.value = payload;
  detailDialog.value = true;
}

async function handleScan() {
  if (!scanInput.value) return;
  try {
    const { data } = await api.post("/loans/scan", { inventory_number: scanInput.value });
    const device = devices.value.find((d) => d.id === data.device_id);
    if (data.action === "loan") {
      openLoanModal(device || { id: data.device_id, name: data.inventory_number });
    } else {
      openReturnModal(device || { id: data.device_id, name: data.inventory_number });
    }
  } catch (err) {
    console.error(err);
  } finally {
    scanInput.value = "";
  }
}

function statusColor(name) {
  if (name === "available") return "success";
  if (name === "loaned") return "warning";
  return "info";
}

function isAvailable(device) {
  return device?.status?.name === "available";
}

function isMaintenance(device) {
  return device?.status?.name === "maintenance";
}

function isLoaned(device) {
  return device?.status?.name === "loaned";
}

function hasRole(role) {
  return currentUser.value.roles?.includes(role);
}

function canAccessDevice(device) {
  const roles = currentUser.value.roles || [];
  const level = device?.security_level || "standard";
  if (level === "standard") return true;
  if (level === "avance") return roles.some((r) => ["gestionnaire", "expert", "admin"].includes(r));
  if (level === "critique") return roles.some((r) => ["expert", "admin"].includes(r));
  return false;
}

function canLoan(device) {
  return !isMaintenance(device) && isAvailable(device) && canAccessDevice(device);
}

function canReturn(device) {
  return !isMaintenance(device) && isLoaned(device) && canAccessDevice(device);
}

function logout() {
  localStorage.removeItem("access_token");
  setAuthToken();
  router.push({ name: "login" });
}

function handleAuthError(err) {
  if (err?.response?.status === 401) {
    logout();
    return true;
  }
  return false;
}

onMounted(async () => {
  await loadCurrentUser();
  await loadCatalog();
  await loadUsers();
  await loadDevices();
});
</script>

<template>
  <v-app>
    <div class="bg-hero" />
      <v-app-bar color="primary" dark flat class="app-bar-elevated">
        <v-app-bar-title class="font-weight-bold">Inventaire et prêts</v-app-bar-title>
        <v-spacer />
      <div class="d-flex align-center mr-4">
        <v-chip class="mr-3" color="accent" variant="elevated" prepend-icon="mdi-account">
          {{ currentUser.username }}
        </v-chip>
        <v-btn
          v-if="isAdmin"
          variant="tonal"
          size="small"
          class="mr-3"
          prepend-icon="mdi-account-multiple"
          @click="openUserDialog"
        >
          Gérer les rôles
        </v-btn>
        <v-btn
          variant="tonal"
          size="small"
          class="mr-3"
          prepend-icon="mdi-logout"
          @click="logout"
        >
          Déconnexion
        </v-btn>
        <v-switch
          v-if="isAdmin"
          v-model="adminMode"
          hide-details
          inset
          color="success"
          class="mr-3"
          :label="adminMode ? 'Mode admin' : 'Lecture seule'"
          @click.stop="toggleAdminMode"
        />
        <v-chip v-else color="secondary" variant="tonal" prepend-icon="mdi-lock">
          Lecture seule
        </v-chip>
      </div>
      <v-text-field
        v-model="scanInput"
        label="Scan ou saisie du numéro"
        hide-details
        density="compact"
        variant="outlined"
        style="max-width: 260px"
        @keyup.enter="handleScan"
      />
      <v-tooltip text="Détecter prêt/retour par numéro" location="bottom">
        <template #activator="{ props }">
          <v-btn class="ml-2" color="secondary" v-bind="props" @click="handleScan">Détecter</v-btn>
        </template>
      </v-tooltip>
      <v-btn
        class="ml-2"
        icon
        variant="tonal"
        color="accent"
        :title="isDark ? 'Mode clair' : 'Mode sombre'"
        @click="toggleTheme"
      >
        <v-icon :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'" />
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid class="py-8 layout-shell">
        <v-card class="mb-4 filter-card" flat>
          <v-card-text>
            <v-row align="center" class="py-2">
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="search"
                  label="Recherche"
                  prepend-inner-icon="mdi-magnify"
                  clearable
                  @keyup.enter="loadDevices"
                  @blur="loadDevices"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="filterStatus"
                  :items="statuses"
                  item-title="name"
                  item-value="id"
                  label="État"
                  clearable
                  @update:model-value="loadDevices"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="filterType"
                  :items="types"
                  item-title="name"
                  item-value="id"
                  label="Type"
                  clearable
                  @update:model-value="loadDevices"
                />
              </v-col>
              <v-col cols="12" md="3" class="text-right">
                <v-btn
                  color="primary"
                  prepend-icon="mdi-plus"
                  @click="openCreateDialog"
                  :disabled="isReadOnly"
                >
                  Nouvel appareil
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card class="elevated-surface">
          <v-data-table
            :headers="[
              { title: 'Inventaire', key: 'inventory_number' },
              { title: 'Nom', key: 'name' },
              { title: 'Lieu', key: 'location' },
              { title: 'Type', key: 'type.name' },
              { title: 'Niveau', key: 'security_level' },
              { title: 'État', key: 'status.name' },
              { title: 'Actions', key: 'actions', sortable: false },
            ]"
            :items="devices"
            :loading="loading"
            class="elevated-surface__table"
            @click:row="(rowEvent, rowData) => openDetail(rowData?.item?.raw || rowData?.item || rowData)"
          >
            <template #item.location="{ item }">
              <span class="text-medium-emphasis">{{ item.location || '—' }}</span>
            </template>
            <template #item.type.name="{ item }">
              <span class="text-capitalize">{{ item.type?.name || 'Non défini' }}</span>
            </template>
            <template #item.security_level="{ item }">
              <v-chip size="small" color="secondary" variant="tonal" class="text-capitalize">
                {{
                  item.security_level === 'critique'
                    ? 'Critique'
                    : item.security_level === 'avance'
                      ? 'Avancé'
                      : 'Standard'
                }}
              </v-chip>
            </template>
            <template #item.status.name="{ item }">
              <v-chip :color="statusColor(item.status?.name)" size="small" class="text-capitalize">
                {{ item.status?.name || 'Non défini' }}
              </v-chip>
            </template>
            <template #item.actions="{ item }">
              <v-tooltip text="Enregistrer un prêt" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    color="primary"
                    @click.stop="openLoanModal(item)"
                    :disabled="!canLoan(item)"
                  >
                    <v-icon icon="mdi-login" />
                  </v-btn>
                </template>
              </v-tooltip>
              <v-tooltip text="Enregistrer un retour" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    color="success"
                    class="ml-1"
                    @click.stop="openReturnModal(item)"
                    :disabled="!canReturn(item)"
                  >
                    <v-icon icon="mdi-logout" />
                  </v-btn>
                </template>
              </v-tooltip>
              <v-tooltip text="Modifier l'appareil" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    class="ml-1"
                    color="secondary"
                    @click.stop="openEditDialog(item)"
                    :disabled="isReadOnly"
                  >
                    <v-icon icon="mdi-pencil" />
                  </v-btn>
                </template>
              </v-tooltip>
              <v-tooltip text="Supprimer l'appareil" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    color="error"
                    class="ml-1"
                    @click.stop="confirmDelete(item)"
                    :disabled="isReadOnly"
                  >
                    <v-icon icon="mdi-delete" />
                  </v-btn>
                </template>
              </v-tooltip>
            </template>
          </v-data-table>
          <div class="mt-3 text-caption text-medium-emphasis px-4 pb-4">
            {{ total }} appareil(s)
          </div>
        </v-card>
      </v-container>
    </v-main>

    <!-- Device dialog -->
    <v-dialog v-model="deviceDialog" max-width="600">
      <v-card>
        <v-card-title class="text-h6">
          {{ isEdit ? "Modifier l'appareil" : "Nouvel appareil" }}
        </v-card-title>
        <v-card-text>
          <v-text-field v-model="deviceForm.inventory_number" label="Numéro d'inventaire" />
          <v-text-field v-model="deviceForm.name" label="Nom" />
          <v-select
            v-model="deviceForm.type_id"
            :items="types"
            item-title="name"
            item-value="id"
            label="Type"
          />
          <v-select
            v-model="deviceForm.security_level"
            :items="securityLevels"
            item-title="title"
            item-value="value"
            label="Niveau de sécurité"
          />
          <v-select
            v-model="deviceForm.status_id"
            :items="statuses"
            item-title="name"
            item-value="id"
            label="État"
          />
          <v-text-field v-model="deviceForm.location" label="Emplacement (stock)" />
          <v-textarea v-model="deviceForm.description" label="Description" rows="3" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="deviceDialog = false">Annuler</v-btn>
          <v-btn color="primary" @click="saveDevice">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirmation -->
    <v-dialog v-model="deleteDialog" max-width="420">
      <v-card>
        <v-card-title>Supprimer l'appareil ?</v-card-title>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="deleteDialog = false">Annuler</v-btn>
          <v-btn color="error" @click="deleteDevice">Supprimer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Loan dialog -->
    <v-dialog v-model="loanDialog" max-width="520">
      <v-card>
        <v-card-title>Enregistrer un prêt</v-card-title>
        <v-card-text>
          <div class="mb-2 font-weight-medium">{{ selectedDevice?.name }}</div>
          <v-select
            v-model="loanForm.borrower"
            :items="users"
            item-title="display_name"
            item-value="username"
            label="Utilisateur"
            clearable
            searchable
            @update:model-value="(val)=>{const u=users.find(x=>x.username===val); loanForm.borrower_display_name = u?.display_name || '';}"
          />
          <div class="text-caption text-medium-emphasis mb-3">
            La liste contient les utilisateurs de test. Assure-toi d'avoir initialisé la base (`init_db`).
          </div>
          <v-text-field
            v-model="loanForm.usage_location"
            label="Lieu d'utilisation"
            placeholder="Ex: Salle TP1, atelier, labo RF..."
          />
          <v-text-field
            v-model="loanForm.due_date"
            type="date"
            label="Date de retour prévue (optionnel)"
          />
          <v-textarea v-model="loanForm.notes" label="Notes" rows="2" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="loanDialog = false">Annuler</v-btn>
          <v-btn color="primary" @click="submitLoan">Valider le prêt</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Return dialog -->
    <v-dialog v-model="returnDialog" max-width="520">
      <v-card>
        <v-card-title>Enregistrer un retour</v-card-title>
        <v-card-text>
          <div class="mb-2 font-weight-medium">{{ selectedDevice?.name }}</div>
          <v-textarea v-model="returnForm.notes" label="Notes de retour" rows="3" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="returnDialog = false">Annuler</v-btn>
          <v-btn color="success" @click="submitReturn">Valider le retour</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- User role manager -->
    <v-dialog v-model="userDialog" max-width="720">
      <v-card>
        <v-card-title>Gestion des rôles</v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-3">
            Seuls les administrateurs peuvent modifier les rôles. Les utilisateurs LDAP doivent exister pour être associés ici.
          </v-alert>
          <v-table density="compact">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Nom affiché</th>
                <th>Rôles</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in managedUsers" :key="user.username">
                <td class="font-weight-medium">{{ user.username }}</td>
                <td>
                  <v-text-field
                    v-model="user.display_name"
                    variant="underlined"
                    density="compact"
                    hide-details
                    @change="saveUserRoles(user)"
                  />
                </td>
                <td style="min-width: 260px;">
                  <v-select
                    v-model="user.roles"
                    :items="roleOptions"
                    multiple
                    chips
                    density="compact"
                    variant="underlined"
                    hide-details
                    @update:model-value="() => saveUserRoles(user)"
                  />
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="userDialog = false">Fermer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Detail dialog -->
    <v-dialog v-model="detailDialog" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <div>
            <div class="text-h6">{{ selectedDevice?.name }}</div>
            <div class="text-caption text-medium-emphasis">#{{ selectedDevice?.inventory_number }}</div>
          </div>
          <v-spacer />
          <v-chip :color="statusColor(selectedDevice?.status?.name || '')" size="small" class="text-capitalize">
            {{ selectedDevice?.status?.name }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6">
              <div class="text-subtitle-2 mb-1">Type</div>
              <div class="text-body-2">{{ selectedDevice?.type?.name }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-subtitle-2 mb-1">Niveau de sécurité</div>
              <div class="text-body-2 text-capitalize">
                {{
                  selectedDevice?.security_level === 'critique'
                    ? 'Critique'
                    : selectedDevice?.security_level === 'avance'
                      ? 'Avancé'
                      : 'Standard'
                }}
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-subtitle-2 mb-1">Emplacement (stock)</div>
              <div class="text-body-2">{{ selectedDevice?.location || '—' }}</div>
            </v-col>
            <v-col cols="12">
              <div class="text-subtitle-2 mb-1">Description</div>
              <div class="text-body-2">{{ selectedDevice?.description || '—' }}</div>
            </v-col>
          </v-row>
          <v-divider class="my-3" />
          <div class="text-subtitle-1 mb-2">Prêt en cours</div>
          <div v-if="selectedDevice?.current_loan">
            <v-row>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-1">Emprunteur</div>
                <div class="text-body-2">
                  {{ selectedDevice.current_loan.borrower_display_name || selectedDevice.current_loan.borrower }}
                </div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-1">Date de prêt</div>
                <div class="text-body-2">
                  {{ new Date(selectedDevice.current_loan.loaned_at).toLocaleString() }}
                </div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-1">Lieu d'utilisation</div>
                <div class="text-body-2">{{ selectedDevice.current_loan.usage_location || '—' }}</div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-1">Date de retour prévue</div>
                <div class="text-body-2">
                  {{ selectedDevice.current_loan.due_date ? new Date(selectedDevice.current_loan.due_date).toLocaleString() : '—' }}
                </div>
              </v-col>
              <v-col cols="12">
                <div class="text-subtitle-2 mb-1">Notes</div>
                <div class="text-body-2">{{ selectedDevice.current_loan.notes || '—' }}</div>
              </v-col>
            </v-row>
          </div>
          <div v-else class="text-medium-emphasis text-body-2">Aucun prêt en cours.</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="detailDialog = false">Fermer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<style scoped>
.bg-hero {
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at 20% 20%, rgba(123, 197, 255, 0.25), transparent 35%),
    radial-gradient(circle at 80% 10%, rgba(98, 167, 255, 0.15), transparent 30%),
    linear-gradient(135deg, rgba(18, 39, 68, 0.9), rgba(18, 39, 68, 0.6));
  opacity: 0.4;
  pointer-events: none;
  z-index: 0;
}

.app-bar-elevated {
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.layout-shell {
  position: relative;
  z-index: 1;
}

.elevated-surface {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(15, 26, 54, 0.12);
}

.elevated-surface__table :deep(.v-data-table__wrapper) {
  background: transparent;
}

.v-main {
  background: transparent;
}

.filter-card {
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15, 26, 54, 0.08);
}
</style>
