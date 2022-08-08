

<template>
  <main>

    <div class="font-semibold text-3xl text-teal-500 tracking-tight content-center text-center mt-4">{{testsStore.test}}</div>

    
<!--  

  <div class="w-96">
    <div class="flex justify-between mb-1 ">
      <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
      <span class="text-sm font-medium text-teal-500 dark:text-white">{{status}}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
    </div>
  </div> -->
  </main>
</template>



<script lang="ts">
import axios from 'axios';
import { useTestsStore } from '@/stores/UseTestsStore.ts';
import { storeToRefs } from 'pinia'


export default {
  components: {
},
  props: {
  },
  setup() {
    const testsStore = useTestsStore();
    return {testsStore}
  },
  data: () => ({
    ActiveTests: [],
    LastValue: 0,
    status: "No information available yet",
    percent: 0
    }),

   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';


  },
  computed: {
    progressStyle() {
      return "width: " + this.percent.toString() + "%;"
    }
  }
};
</script>

<style scoped>

#ImplementationsView {
display: flex;
    /* justify-content: space-evenly; */   
    height: 65vh;
}

.test{
    flex: 1;
}

.progress {
  width:  v-bind('percent')%;
}

</style>