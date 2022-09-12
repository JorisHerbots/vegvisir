<script setup lang="ts">
</script>

<template>
  <main>
      <div class="text-center text-5xl font-medium mt-8 mb-32">
        Welcome to Vegvisir!
      </div>
  
  <div v-if="!passwordStore.password_is_set" class="content-center text-xl text-center font-bold w-screen mb-32 ">
    Vegvisir needs your sudo password to work, please enter it <br>
  <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded m-4 py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500 z-1" v-model="password" default="" type="password" id="inline-full-name" placeholder="password">
    
    <button @click="sendPassword" class=" mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
        Submit
    </button>
  </div>

    <div class="flex">
      <div class="text-center text-xl font-medium mt-8 flex-1 ml-4 mr-4"> 
        <div class="text-3xl">Would you like to create a new test? <br> </div>

        <button @click="$router.push({ path: '/configure_test' })" class="mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Create Test
        </button>
      <br>
        A test consists of "testcases" and "implementations": clients, shapers, servers <br>
      <br>
        <ul class="text-left ml-24 text-xl font-medium list-disc">
          <li class="text-left text-xl font-medium">Testcase: scenario describing the content to download and stop condition</li>
          <li class="text-left text-xl font-medium">Client: the client downloading the content</li>
          <li class="text-left text-xl font-medium">Shaper: network simulator</li>
          <li class="text-left text-xl font-medium">Server: the webserver hosting the content </li>
        </ul>
        <br>

        Vegvisir is extensible: you can create your own testcases and implementations, please see the documentation on how to do so.  <br>
      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1">
        <div class="text-3xl">Would you like to import and reproduce a test? <br></div>
        <button @click="" class=" mt-4 mb-8 bbg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Import Test
        </button>

        <br>
        The test will be imported and automatically be ran again to reproduce the results

      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1 mr-4 ml-4">
        <div class="text-3xl">Would you like to view past and currently running tests? <br></div>
        <button @click="$router.push({ path: '/progress' })" class=" mt-4 mb-8 bg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            View
        </button>

        <br>
        Past tests can be viewed here as can running tests. Clicking on a test opens the detailed information where you can view the created log files, as well as the configuration of the test. If you would like to re-test a slightly different scenario you can always "edit and rerun" the test.

      </div>

      <div class="text-center text-xl font-medium mt-8 flex-1 hidden">
        <div class="text-3xl">Would you like to break the paraplu?<br></div>
        <a href="https://jherbots.info/"><button class=" mt-4 mb-8 bg-transparent hover:bg-teal-500 text-teal-500 font-semibold hover:text-white py-2 px-4 border border-teal-500 hover:border-transparent rounded">
            Break
        </button>
        </a>
      </div>


    </div>

  </main>
</template>


<script lang="ts">
import axios from 'axios';
import { usePasswordStore }  from '@/stores/UsePasswordStore.ts';

export default {
  components: {
},
  props: {
    
  },
  setup() {
    const passwordStore = usePasswordStore();

    return { passwordStore }
  },
  data: () => ({
    password: String
    }),
   created() {
    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
  },
  methods: {
    sendPassword() {
      this.passwordStore.setPassword(this.password);
    }
  }
}
</script>