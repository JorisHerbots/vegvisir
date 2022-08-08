

<template>
  <main>

    <div class="font-semibold text-3xl text-teal-500 tracking-tight content-center text-center mt-4">{{testsStore.test}}</div>

    <button @click="EditAndRerun" class="bg-transparent hover:bg-orange-500 text-orange-500 font-semibold hover:text-white py-2 px-4 border border-orange-500 hover:border-transparent rounded">
      Edit and rerun
    </button>
    
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
  methods: {
    EditAndRerun() {
      // Deep copy
      let temp = JSON.parse(JSON.stringify(this.testsStore.test));
      console.log(temp); 
      temp.name = temp.name + "(1)";


      this.testsStore.test = temp
      this.$router.push({ path: '/configure' })
    }


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