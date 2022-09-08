

<template>
  <main>

    <p/>
    <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500 m-16 w-64" id="inline-full-name" type="text" v-model="CreateImagesetName">
    <button  class="absolute bg-transparent mt-16 left-128 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded" @click="CreateImageset()">
        Create Imageset
    </button>

    <button id="create-imageset-with-all-images-button"  class="absolute bg-transparent mt-16 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded" @click="this.imagesetsStore.requestCreateImageset(this.CreateImagesetName);">
        Create Imageset With all Images
    </button>

    <!-- list of all available images with checkboxes -->
    <div id="image-selection-list" class="ml-4 text-2xl mb-16 h-96 overflow-scroll overflow-x-hidden">
      <ul>  
        <div v-for="(item, index) in implemenationsStore.implementations">    
        <li class="ml-4 h-16" v-if="(!('client' in item)) || (item.client.type === 'docker')">
             <hr>
            <input type="checkbox" id=item name=item class="mb-2" @change="ImageCheckboxToggle(index, item, $event)" :checked="false"> {{index}}
            {{index}} 
            <br/>
            {{item.image}}
        </li>
        </div>  
      </ul>
  </div>

    <!-- list of available imagesets -->
    <div class="flex flex-row mt-16 ml-4 mr-4">
      <div id="available_imagesets" class="grow mr-8">

        <div class="text-2xl text-center font-semibold mb-4">
          Available imagesets
        </div>

        <ul class="ml-4 text-2xl mb-16">
          <li class="h-16" v-for="(item, index) in imagesetsStore.imagesets_available">
            <hr>
            {{item}}
          
            <button @click="ImportImageset(item)"  class="absolute bg-transparent mt-2 right-4 z-1 bg-green-500 font-semibold text-white py-1 px-2 border border-transparent rounded">
              Import
            </button>

          </li>
          <hr>
        </ul>
      
      </div>

      <!-- list of loaded imagesets with checkboxes to active/deactive + delete -->
      <div id="loaded_imagesets" class="grow ml-8">
        <div class="text-2xl text-center font-semibold mb-4">
        Loaded imagesets
        </div>


        <ul class="ml-4 text-2xl">
          <li class="h-16" v-for="(item, index, key) in imagesetsStore.imagesets_loaded">
            <hr>
            <input type="checkbox" id=item name=item class="mb-2" @change="LoadedImagesetCheckboxToggle(index, $event)" :checked="item"> {{index}}
              
              <button @click.stop.prevent @click="RemoveImageset(index)" class="absolute bg-transparent hover:bg-red-500 mt-2 right-32 text-red-700 font-semibold hover:text-white py-1 px-2 border border-red-500 hover:border-transparent rounded">
              Remove
              </button>
              <button @click="ExportImageset(index)"  class="absolute bg-transparent mt-2 right-4 z-1 bg-green-500 font-semibold text-white py-1 px-2 border border-transparent rounded">
              Export
            </button>
          </li>
        <hr>
        </ul>
      </div> 
    </div>


  </main>
</template>



<script lang="ts">
import axios from 'axios';
import { useImagesetsStore } from '@/stores/UseImagesetsStore.ts';
import { useTestsStore } from '@/stores/UseTestsStore.ts';
import { storeToRefs } from 'pinia'
import { useImplementationsStore } from '@/stores/UseImplementationsStore';


export default {
  components: {
},
  props: {
  },
  setup() {
    const imagesetsStore = useImagesetsStore();
    const implemenationsStore = useImplementationsStore();

    imagesetsStore.requestLoadedImagesetsUpdate();
    imagesetsStore.requestAvailableImagesetsUpdate();
    implemenationsStore.requestImplementationsUpdate();

    return {imagesetsStore, implemenationsStore};
  },
  data: () => ({
    CreateImagesetName: "",
    CheckedImages: {} 
  }),
   created() {
  },
  methods: {
    ImportImageset(imageset_file) {
      this.imagesetsStore.requestImportImageset(imageset_file);
    },
    ExportImageset(imageset_name) {
      this.imagesetsStore.requestExportImageset(imageset_name);
    },
    LoadedImagesetCheckboxToggle(imageset_name, event) {
      if (event.target.checked) {
        this.imagesetsStore.requestActivateImageset(imageset_name);
      }
      else {
        this.imagesetsStore.requestDisableImageset(imageset_name);
      }
    },
    ImageCheckboxToggle(index, image, event) {
      if (event.target.checked) {
        this.CheckedImages[index] = image
      }
      else {
        delete this.CheckedImages[index]
      }      
      console.log(this.CheckedImages)
    },
    CreateImageset() {
        this.imagesetsStore.requestCreateImagesetWithImplementations(this.CreateImagesetName, this.CheckedImages)
    },
    RemoveImageset(imageset_name) {
      this.imagesetsStore.requestRemoveImageset(imageset_name);
    }
  }
};
</script>

<style scoped>

input[type=checkbox] {
    transform: scale(1.5);
}

#create-imageset-with-all-images-button {
  left: 25%;
}

</style>