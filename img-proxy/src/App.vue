<script lang="ts">
import {useLoginStore} from "@/stores/login";
import LoginForm from "@/components/LoginForm.vue";


export default {
  components: {LoginForm},
  setup() {
    const loginStore = useLoginStore()
    return {loginStore}
  },
  data() {
    return {

    }
  },
  computed: {
    userProfile() {
      return this.loginStore.userProfile
    }
  },
  mounted() {
    document.title = this.appName
  },
  methods: {
    openLoginBox() {
      this.loginStore.openBox();
      return false;
    },
    logout() {
      this.loginStore.logout();
    }
  }
}
</script>

<template>
  <div class="page">
    <!-- Panel menu -->
    <nav class="menu">
      <ul>
        <li><RouterLink to="/" class="bi bi-image" title="Images"><span>Images</span></RouterLink></li>
        <li>
          <RouterLink :to="{name: 'collections'}" class="bi bi-images" title="Collections"><span>Collections</span></RouterLink>
        </li>
      </ul>
      <ul class="footer">
        <li v-if="userProfile == null"><a href="#" @click="openLoginBox" class="bi bi-person" title="Login"><span>Login</span></a></li>
        <li v-else><a href="#" @click="logout" class="bi bi-person" title="Logout"><span>Logout {{ userProfile.username }}</span></a></li>
      </ul>
    </nav>
    <router-view />
  </div>
  <LoginForm></LoginForm>
</template>

<style scoped>

.page {
  display: flex;
  flex-direction: row;
  height: 100%; /* Nastaví výšku na 100% výšky okna */
  transition-property: margin-right;
  transition-duration: 0.3s;
}

.menu {
  width: 180px;
  background-color: #333;
  color: white;
  padding: 20px;
  /* Nastaví menu na 100% výšky okna */
  height: 100vh;
  border-right: 1px solid rgba(92, 92, 92, 0.5);
}

.menu ul {
  list-style: none;
  padding: 0;
}

.menu li {
  margin-bottom: 10px;
}

.menu a {
  color: white;
  text-decoration: none;

}

.menu a span {
  margin-left: 10px;
}

.footer {
  position: absolute;
  bottom: 0;
  margin-top: 1rem;
  margin-bottom: 0;
}


@media (max-width: 1024px) {
  .menu {
    width: 30px;
    padding: 5px;
  }
  .menu a span {
    display: none;
  }
}
</style>

<!--<style scoped>-->
<!--header {-->
<!--  line-height: 1.5;-->
<!--  max-height: 100vh;-->
<!--}-->

<!--.logo {-->
<!--  display: block;-->
<!--  margin: 0 auto 2rem;-->
<!--}-->

<!--nav {-->
<!--  width: 100%;-->
<!--  font-size: 12px;-->
<!--  text-align: center;-->
<!--  margin-top: 2rem;-->
<!--}-->

<!--nav a.router-link-exact-active {-->
<!--  color: var(&#45;&#45;color-text);-->
<!--}-->

<!--nav a.router-link-exact-active:hover {-->
<!--  background-color: transparent;-->
<!--}-->

<!--nav a {-->
<!--  display: inline-block;-->
<!--  padding: 0 1rem;-->
<!--  border-left: 1px solid var(&#45;&#45;color-border);-->
<!--}-->

<!--nav a:first-of-type {-->
<!--  border: 0;-->
<!--}-->

<!--@media (min-width: 1024px) {-->
<!--  header {-->
<!--    display: flex;-->
<!--    place-items: center;-->
<!--    padding-right: calc(var(&#45;&#45;section-gap) / 2);-->
<!--  }-->

<!--  .logo {-->
<!--    margin: 0 2rem 0 0;-->
<!--  }-->

<!--  header .wrapper {-->
<!--    display: flex;-->
<!--    place-items: flex-start;-->
<!--    flex-wrap: wrap;-->
<!--  }-->

<!--  nav {-->
<!--    text-align: left;-->
<!--    margin-left: -1rem;-->
<!--    font-size: 1rem;-->

<!--    padding: 1rem 0;-->
<!--    margin-top: 1rem;-->
<!--  }-->
<!--}-->
<!--</style>-->
