

<template>
  <main>

    <div v-if="Object.keys(testsStore.tests).length <= 0" class="text-gray-300 text-center text-5xl z--40 mt-24 text-center">
      No running or completed tests (yet)
    </div>



    <ul>
      <li  v-for="(item, index) in testsStore.tests">
        <TestCard :Test='item'></TestCard>
     </li>
    </ul>

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
    testsStore.requestRunningTestStatusUpdate();
    return {testsStore}
  },
  data: () => ({}),
   created() {
    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
  },
};
</script>

<style scoped>
</style>