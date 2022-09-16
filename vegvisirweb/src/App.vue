

<template>
  <!-- <header> -->

  <nav class="flex items-center justify-between flex-wrap bg-teal-500 p-6">
    <div class="flex items-center flex-shrink-0 text-white mr-6">
      <!-- <svg class="fill-current h-8 w-8 mr-2" width="54" height="54" viewBox="0 0 54 54" xmlns="http://www.w3.org/2000/svg"><path d="M13.5 22.1c1.8-7.2 6.3-10.8 13.5-10.8 10.8 0 12.15 8.1 17.55 9.45 3.6.9 6.75-.45 9.45-4.05-1.8 7.2-6.3 10.8-13.5 10.8-10.8 0-12.15-8.1-17.55-9.45-3.6-.9-6.75.45-9.45 4.05zM0 38.3c1.8-7.2 6.3-10.8 13.5-10.8 10.8 0 12.15 8.1 17.55 9.45 3.6.9 6.75-.45 9.45-4.05-1.8 7.2-6.3 10.8-13.5 10.8-10.8 0-12.15-8.1-17.55-9.45-3.6-.9-6.75.45-9.45 4.05z"/></svg> -->
      <span class="font-semibold text-xl tracking-tight">Vegvisir</span>
    </div>
    <div class="block lg:hidden">
      <button class="flex items-center px-3 py-2 border rounded text-teal-200 border-teal-400 hover:text-white hover:border-white">
        <svg class="fill-current h-3 w-3" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><title>Menu</title><path d="M0 3h20v2H0V3zm0 6h20v2H0V9zm0 6h20v2H0v-2z"/></svg>
      </button>
    </div>
    <div class="w-full block flex-grow lg:flex lg:items-center lg:w-auto">
      <div class="text-sm lg:flex-grow">
        <RouterLink to="/" class="block mt-4 lg:inline-block lg:mt-0 text-teal-200 hover:text-white mr-4">Home</RouterLink>
        <RouterLink to="/configure_test" class="block mt-4 lg:inline-block lg:mt-0 text-teal-200 hover:text-white mr-4">Test</RouterLink> 
        <RouterLink to="/progress" class="block mt-4 lg:inline-block lg:mt-0 text-teal-200 hover:text-white mr-4">Progress</RouterLink> 
        <RouterLink to="/configure_docker" class="block mt-4 lg:inline-block lg:mt-0 text-teal-200 hover:text-white mr-4">Docker</RouterLink> 
      </div>
      <!-- <div>
        <a href="#" class="inline-block text-sm px-4 py-2 leading-none border rounded text-white border-white hover:border-transparent hover:text-teal-500 hover:bg-white mt-4 lg:mt-0">Download</a>
      </div> -->
    </div>
    <button @click="showShutdown = true;" class="bg-transparent bg-red-500 font-semibold text-white py-2 px-4 border border-red-500 hover:border-transparent rounded">
      Shutdown
    </button>
  </nav>

  <!-- <ImplementationList :listItems="listItemsTest"></ImplementationList> -->
  <!-- <ImplementationCard Name="Chromium" Description="Version 94.0.02"></ImplementationCard>
  <ImplementationCard Name="Test" Description="Test2"></ImplementationCard> -->

    <!-- <img alt="Vue logo" class="logo" src="@/assets/logo.svg" width="125" height="125" /> -->
<!--   
    <div class="wrapper">
      <nav>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/about">About</RouterLink>
        <RouterLink to="/about">About2</RouterLink>
      </nav>
    </div> -->
  <!-- </header> -->
  <div v-if="showShutdown">
  <ShutdownConfirmModal @cancel="showShutdown = false;" @shutdown="shutdown" ></ShutdownConfirmModal>
  </div>
  <RouterView />


</template>


<script lang="ts">
import axios from 'axios';
import { ref, watch } from 'vue';
import { RouterLink, RouterView } from 'vue-router'
import ImplementationCard from './components/ImplementationCard.vue'
import ImplementationList from './components/ImplementationList.vue'
import ShutdownConfirmModal from './components/ShutdownConfirmModal.vue'

export default {
  components: {
      ShutdownConfirmModal
  },
  setup() {
    const showShutdown = ref<Boolean>(false);

    return { showShutdown}

  },
  methods: {
    shutdown() {
      axios({
          url: "http://127.0.0.1:5000/Shutdown",
          method: "GET"
        })   
        .then(response => {
          this.$router.push({ path: '/shutting_down' })
          this.showShutdown = false
        })
        .catch(error => {
          this.$router.push({ path: '/shutting_down' })
          this.showShutdown = false
        }) 
    }
  },
  computed: {
  },
  data: () => ({
  }),
  created() {
  }
}

</script>
