

<template>
  <main>

      <li  v-for="(item, index) in testsStore.tests">
        <TestCard :Test='item'></TestCard>
     </li>
  

  </main>
</template>



<script lang="ts">
import axios from 'axios';
import TestCard from '@/components/TestCard.vue';
import { useTestsStore } from '@/stores/UseTestsStore.ts';
import { storeToRefs } from 'pinia'


export default {
  components: {
    TestCard
},
  props: {
  },
  setup() {
    const testsStore = useTestsStore();

    return {testsStore}
  },
  data: () => ({}),
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
  }
};
</script>

<style scoped>
</style>