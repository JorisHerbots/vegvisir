


<template>
  <div class="outerC">
  <div id="list" class="bg-white border">
    
      <li  v-for="(item, index) in listItems">
        <TestCaseCard @clicked="CardClicked" @RemoveClicked="CardRemoveClicked" :Implementation="item" :CanBeRemoved="CanBeModified"></TestCaseCard>
     </li>
  
    
    </div>
    <div v-if="CanBeModified">
        <button @click="AddClicked()" id="but" class="absolute bg-transparent bottom-4 right-4 z-1 hover:bg-green-500 text-green-700 font-semibold hover:text-white py-2 px-4 border border-green-500 hover:border-transparent rounded">
        Add
      </button>
    </div>
  </div>

  <!-- <ImplementationCard  Name="item.name" Description="item.description"></ImplementationCard> -->
</template>



<script lang="ts">
import TestCaseCard from './TestCaseCard.vue'

export default {
  name: "TestCaseList",
  props: {
    listItems: Array,
    CanBeModified: false
  },
  components: {
    TestCaseCard
  },
  data: () => ({}),
  created() {
    console.log(this.listItems);
  },
  methods: {
    CardClicked(arg) {
      this.$emit("CardClicked", arg);
    },
    CardRemoveClicked(arg) {
      this.$emit("CardRemoveClicked", arg);
    },
    AddClicked() {
      this.$emit("AddClicked", true)
    }
  }
};
</script>

<style>


.outerC {   
  width: auto;
  list-style-type: none;
  height: inherit}

#list {
  height: inherit;
  width: inherit;
  list-style-type: none;
  overflow: scroll;
  overflow-x: hidden;
}


</style>