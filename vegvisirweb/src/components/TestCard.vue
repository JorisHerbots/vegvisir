
<template>


<div @click="Clicked()"  class="card block pl-6 pr-6 pt-2 pb-2 max-w-none bg-white  border border-gray-200 shadow-md hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700">
    <div class="flex flex-row">
    
    <div class="grow">
    <h5 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{{Test.name}}</h5>
    
    <p class="font-normal text-gray-700 dark:text-gray-400">{{date}}</p>
    <p class="font-normal text-gray-700 dark:text-gray-400">{{Test.id}}</p>
    </div>

    <div v-if="Test.status === 'running'"> 
      <div class="w-96 mr-64">
        <div class="flex justify-between mb-1 ">
          <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
          <span class="text-sm font-medium text-teal-500 dark:text-white">{{testsStore.status}}</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
          <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
        </div>
      </div>
    </div>
    <div v-if="Test.status !== 'running'"> 
      <div  class="w-96 mr-64 mt-4">
          <div v-if="Test.status === 'waiting'"> 
            <span class="text-base font-medium text-grey-500 dark:text-white">Waiting</span>
          </div>
          <div v-if="Test.status === 'done'"> 
            <span class="text-base font-medium text-teal-500 dark:text-white">Done</span>
          </div>
            <div v-if="Test.status === 'idle'"> 
            <span class="text-base font-medium text-stone-500 dark:text-white">Idle</span>
          </div>
      </div>
    </div>

    <div class="flex flex-col justify-center">
    <button @click.stop.prevent @click="RemoveClicked(Test.id)" class="bg-transparent hover:bg-red-500 text-red-700 font-semibold hover:text-white py-2 px-4 border border-red-500 hover:border-transparent rounded">
      Remove
    </button>
    </div>
    </div>
</div>



</template>


<script lang="ts">
import { storeToRefs } from 'pinia'
import { useTestsStore } from '@/stores/UseTestsStore.ts';

export default {
  props: {
    Test: {}
  },
  data: () => ({
    status: "No information available yet",
    percent: 0,
  }),
  setup() {
    const testsStore = useTestsStore();

    return {testsStore};
  },
  created() {
  },
  methods: {
    Clicked() {
      this.testsStore.test = this.Test;
      this.$router.push({ path: '/ViewTest', query: {id: this.Test.id} })
    },
    RemoveClicked(id) {
      this.testsStore.removeTest(id);
    }
  },
  computed: {
    progressStyle() {
      this.percent = this.testsStore.status.split("/").reduce((a,b) => parseInt(a) / parseInt(b)) * 100;
    
      return "width: " + this.percent.toString() + "%;"
    },
    date() {
      var d = new Date(parseInt(this.Test.time_added) * 1000); // The 0 there is the key, which sets the date to the epoch
      return d.toISOString().slice(0, 10) + " " + d.toISOString().slice(11, 19) 
    }
  }
};
</script>

<style>

.card {
  cursor: pointer;
}

</style>