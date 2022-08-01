
<template>


<div @click="Clicked(Implementation.active_id)"  class="card block p-6 max-w-none bg-white  border border-gray-200 shadow-md hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700">
    <div class="flex flex-row">
    
    <div class="grow">
    <h5 class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{{Implementation.url}}</h5>
    
    <p class="font-normal text-gray-700 dark:text-gray-400">{{Implementation.url}}</p>
    </div>
    <div class="flex flex-col justify-center">
    <button @click.stop.prevent @click="RemoveClicked(Implementation.active_id)" class="bg-transparent hover:bg-red-500 text-red-700 font-semibold hover:text-white py-2 px-4 border border-red-500 hover:border-transparent rounded">
      Remove
    </button>
    </div>
    </div>
</div>



</template>


<script lang="ts">
export default {
  props: {
    Implementation: {}
  },
  data: () => ({}),
  methods: {
    Clicked(id) {
      this.$emit("Clicked", id);
    },
    RemoveClicked(id) {
      this.$emit("RemoveClicked", id);
    }
  }
};
</script>

<style>

.card {
  cursor: pointer;
}

</style>