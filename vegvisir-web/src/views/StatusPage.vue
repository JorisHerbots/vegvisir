

<template>
  <main>
 

  <div class="w-96">
    <div class="flex justify-between mb-1 ">
      <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
      <span class="text-sm font-medium text-teal-500 dark:text-white">{{status}}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
    </div>
  </div>
  </main>
</template>



<script lang="ts">
import axios from 'axios';
import ImplementationList from '@/components/ImplementationList.vue'
import AddImplementationModal from '@/components/AddImplementationModal.vue';
import ConfigurationModal from '@/components/ConfigurationModal.vue';
import TestCaseList from '@/components/TestCaseList.vue';
import TestConfigurationModal from '@/components/TestConfigurationModal.vue';



export default {
  components: {
},
  props: {
  },
  data: () => ({
    ActiveTests: [],
    LastValue: 0,
    status: "No information available yet",
    percent: 0,
    }),
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';

    let ws = new WebSocket("ws://127.0.0.1:5000/ws");

    ws.addEventListener('message', function (event) {
      this.status = event.data;
      console.log('Message from server ', event.data);

      let string = event.data;
      string = string.replace(" ", "");
      const myArray = string.split("/")

      this.percent = (parseInt(myArray[0]) / parseInt(myArray[1])) * 100;

    }.bind(this));
    //ws.addEventListener('open', this.openEvent.bind(this));
    ws.addEventListener('open', function (event) {
      ws.send('Hello Server!');
    }.bind(this));

  },
  methods: {

   }
  ,
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