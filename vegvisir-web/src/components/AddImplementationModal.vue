
<template>


<!-- Main modal -->
<div id="defaultModal" tabindex="-1" aria-hidden="true" class="overflow-y-auto overflow-x-none fixed top-0 right-0 left-0 z-50 w-full md:inset-z0">
    <div class="relative p-4 w-full">
        <!-- Modal content -->
        <div id="test" class="relative bg-white rounded-lg shadow dark:bg-gray-700">
            <!-- Modal header -->
            <div class="flex justify-between items-start p-4 rounded-t border-b dark:border-gray-600">
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white">
                    Adding Implementation
                </h3>
                <button type="button" @click="Close" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center dark:hover:bg-gray-600 dark:hover:text-white" data-modal-toggle="defaultModal">
                    <svg aria-hidden="true" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                    <span class="sr-only">Close modal</span>
                </button>
            </div>
            <!-- Modal body -->
            <div class="p-6 space-y-1">
                

                <div class="search-wrapper">
                  <input id="listOfImplementationsSearch" @keydown.esc="Close" @keydown.enter="ChoseTopmost" class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" type="text" v-model="search" placeholder="Search title.."/>
                </div>

                <div id="listOfImplementationsToAdd" class="h-full">
                  <li v-for="(item, index) in filteredList" @click="ClickedImplementation(item.id)" style="list-style: none">
                    <div class="card block p-6 max-w-none bg-white  border border-gray-200 shadow-md hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700" >
                        <div class="flex flex-row">
                        
                        <div class="grow">
                        <h5 class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{{item.id}} </h5>
                        
                        <p class="font-normal text-gray-700 dark:text-gray-400">{{item.id}}</p>
                        </div>
                        <div class="flex flex-col justify-center">
                        </div>
                        </div>
                    </div>                    
                  </li> 
                </div>
          

            </div>
            <!-- Modal footer -->
            <div id="test2" class="absolute right-0 flex items-center p-6 space-x-2 rounded-b border-gray-200 dark:border-gray-600">
                <button data-modal-toggle="defaultModal" type="button" @click="Close" class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">OK</button>
            </div>
        </div>
    </div>
</div>


</template>


<script lang="ts">
export default {
  name: "AddImplementationModal",
  props: {
    AvailableImplementations: {}
  },
  data: () => ({
    search: ""
  }),
  methods: {
    Close() {
      this.$emit("Close");
    },
    ClickedImplementation(id) {
      this.$emit("ClickedImplementation", id);
    },
    // So user can enter (part of) name in search bar and press enter to add implementation
    ChoseTopmost() {
      let list = this.filteredList;
      if (list.length >= 1) {
        this.$emit("ClickedImplementation", list[0].id);
      } 
    }
  },
  computed: {
    filteredList() {
      return this.AvailableImplementations.filter(implementation => {
        return implementation.id.toLowerCase().includes(this.search.toLowerCase())
      })
    }
  },
  mounted(this: ComponentPublicInstance): void {
     document.getElementById("listOfImplementationsSearch").focus();
  }
};
</script>

<style>

.card {
}

#test {
  height: 95vh;
}

#test2 {
  bottom: 0px;
} 

#listOfImplementationsToAdd {
  height: 75vh;
  overflow: auto;
}

</style>