


<template>
  <div class="outer">
  <div id="list" class="bg-white border">
    
      <li  v-for="(item, index) in listItems">
        <ImplementationCard @clicked="CardClicked" @RemoveClicked="CardRemoveClicked" :Implementation="item"></ImplementationCard>
     </li>
  
    
    </div>
        <button @click="AddClicked()" id="but" class="absolute bg-transparent bottom-4 right-4 z-1 hover:bg-green-500 text-green-700 font-semibold hover:text-white py-2 px-4 border border-green-500 hover:border-transparent rounded">
        Add
      </button>
  </div>

  <!-- <ImplementationCard  Name="item.name" Description="item.description"></ImplementationCard> -->
</template>



<script lang="ts">
import ImplementationCard from './ImplementationCard.vue'

export default {
  name: "ImplementationList",
  props: {
    listItems: Array,
  },
  components: {
    ImplementationCard
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


.outer {   
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