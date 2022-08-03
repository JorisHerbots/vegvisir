
<template>


<div @click="Clicked(Test.id)"  class="card block p-6 max-w-none bg-white  border border-gray-200 shadow-md hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700">
    <div class="flex flex-row">
    
    <div class="grow">
    <h5 class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{{Test.name}}</h5>
    
    <p class="font-normal text-gray-700 dark:text-gray-400">{{Test.id}}</p>
    </div>

    <div v-if="Test.status === 'running'"> 
      <div class="w-96 mr-64">
        <div class="flex justify-between mb-1 ">
          <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
          <span class="text-sm font-medium text-teal-500 dark:text-white">{{status}}</span>
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
      </div>
    </div>

    <div class="flex flex-col justify-center">
    <button @click.stop.prevent @click="RemoveClicked(Test.id)" class="bg-transparent hover:bg-red-500 text-red-700 font-semibold hover:text-white py-2 px-4 border border-red-500 hover:border-transparent rounded">
      Open
    </button>
    </div>
    </div>
</div>



</template>


<script lang="ts">
export default {
  props: {
    Test: {}
  },
  data: () => ({
    status: "No information available yet",
    percent: 0
  }),
  created() {
    let ws = new WebSocket("ws://127.0.0.1:5000/ws");

    ws.addEventListener('message', function (event) {
      this.status = event.data;
      console.log('Message from server ', event.data);

      let string = event.data;
      string = string.replace(" ", "");
      const myArray = string.split("/")

      this.percent = (parseInt(myArray[0]) / parseInt(myArray[1])) * 100;

    }.bind(this));

  },
  methods: {
    Clicked(id) {
      this.$emit("Clicked", id);
    },
    RemoveClicked(id) {
      this.$emit("RemoveClicked", id);
    }
  },
  computed: {
    progressStyle() {
      return "width: " + this.percent.toString() + "%;"
    }
  }
};
</script>

<style>

.card {
  cursor: pointer;
}

</style>